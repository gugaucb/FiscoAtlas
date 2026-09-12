from datetime import date
from decimal import Decimal
from django.utils import timezone

from django.core.exceptions import ValidationError
from django.db import models

# Taxonomia legal da Lei 14.754/2023 (RF-AST-006/007): sem inferência
# silenciosa — todo ativo é cadastrado explicitamente com sua natureza.
ASSET_TYPES = [
    ("FOREIGN_EQUITY", "Ação estrangeira"),
    ("FOREIGN_ETF", "ETF estrangeiro"),
    ("REIT", "REIT"),
    ("US_TREASURY", "Treasury americano"),
    ("FOREIGN_BOND", "Título de dívida estrangeiro"),
    ("FOREIGN_FUND", "Fundo estrangeiro"),
    ("CONTROLLED_ENTITY", "Entidade controlada (offshore)"),
    ("TRUST", "Trust"),
    ("UNKNOWN", "Desconhecida"),
]
ACCOUNT_TYPES = [("CASH", "Cash"), ("CUSTODY", "Custódia"), ("MARGIN", "Margem"), ("OTHER", "Outro")]
EVENT_TYPES = [
    ("APORTE", "Aporte (entrada de caixa)"),
    ("WITHDRAWAL", "Retirada (saída de caixa)"),
    ("BUY", "Compra"),
    ("SELL", "Venda"),
    ("DIVIDEND", "Dividendo"),
    ("JUROS", "Juros/rendimento de caixa"),
    ("FEE", "Taxa/corretagem"),
    ("TAX_WITHHELD", "Imposto retido nos EUA"),
    # Corporate actions (RF-CA-001..003): o split altera quantidade e custo
    # unitário; o custo total histórico em BRL permanece inalterado.
    ("STOCK_SPLIT", "Desdobramento (split)"),
    ("REVERSE_SPLIT", "Grupamento (reverse split)"),
    ("CASH_IN_LIEU", "Fração paga em dinheiro (cash-in-lieu)"),
    # RF-CST-003: transferência entre contas do mesmo titular não é alienação
    ("BROKER_TRANSFER_IN", "Transferência de custódia (entrada)"),
    ("BROKER_TRANSFER_OUT", "Transferência de custódia (saída)"),
    # RF-FTC-009: estorno de imposto retido no exterior (ex.: 1042-S)
    ("WITHHOLDING_REFUND", "Restituição de imposto retido no exterior"),
]


class Asset(models.Model):
    ticker = models.CharField(max_length=32, unique=True)
    description = models.CharField(max_length=255)
    asset_type = models.CharField(max_length=32, choices=ASSET_TYPES)
    isin = models.CharField(max_length=12, null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    country_code = models.CharField(max_length=2, default="US")
    is_controlled_entity = models.BooleanField(default=False)
    ownership_share_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.ticker


OWNERSHIP_TYPES = [
    ("INDIVIDUAL", "Individual"),
    ("JOINT", "Conjunta"),
    ("THIRD_PARTY", "Terceiros"),
]


class BrokerAccount(models.Model):
    name = models.CharField("apelido do caixa", max_length=128, blank=True)
    broker_name = models.CharField(max_length=128)
    account_number = models.CharField(max_length=64)
    country_code = models.CharField(max_length=2, default="US")
    currency = models.CharField(max_length=3, default="USD")
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES, default="CASH")
    is_interest_bearing = models.BooleanField(default=False)
    # RF-PER-003: titularidade — fatia do contribuinte em contas conjuntas
    ownership_type = models.CharField(max_length=12, choices=OWNERSHIP_TYPES, default="INDIVIDUAL")
    ownership_share = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    active = models.BooleanField(default=True)

    def clean(self):
        # auditoria-fiscal 06: 0% é permitido como decisão EXPLÍCITA do
        # usuário (conta de terceiros) — nunca como default silencioso.
        if not (Decimal("0.00") <= (self.ownership_share or Decimal(0)) <= Decimal(100)):
            raise ValidationError("ownership_share deve estar entre 0,00 e 100,00.")

    def __str__(self):
        return self.name or f"{self.broker_name} ({self.account_number})"


FOREIGN_TAX_STATES = [
    ("UNDECLARED", "Não declarado"),
    ("NO_WITHHOLDING", "Sem retenção no exterior (declarado pelo contribuinte)"),
    ("RECORDED", "Registrado em ForeignTaxPayment"),
    ("REVIEW_PENDING", "Pendente de revisão documental"),
]


class FinancialEvent(models.Model):
    event_type = models.CharField(max_length=32, choices=EVENT_TYPES)
    account = models.ForeignKey(BrokerAccount, on_delete=models.PROTECT, related_name="events")
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, null=True, blank=True, related_name="events")
    trade_date = models.DateField()
    settle_date = models.DateField(null=True, blank=True)
    # Auditoria-fiscal 10: fato gerador do RENDIMENTO é o recebimento efetivo
    # (ex.: dividendo negociado 31/12 creditado 02/01 pertence ao ano do
    # recebimento). Ganhos de alienação continuam pela trade_date.
    income_receipt_date = models.DateField(null=True, blank=True)
    # Auditoria-fiscal 12: estado declarado do imposto exterior do rendimento
    # — "sem imposto" não é retenção zero presumida; exige declaração
    # explícita (NO_WITHHOLDING) ou fica pendente de reconciliação.
    foreign_tax_state = models.CharField(
        max_length=16, choices=FOREIGN_TAX_STATES, default="UNDECLARED",
    )
    quantity = models.DecimalField(max_digits=24, decimal_places=10, null=True, blank=True)
    price_usd = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    fee_usd = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    amount_usd = models.DecimalField(max_digits=20, decimal_places=8)
    # Auditoria-fiscal 04: o campo tax_usd duplicado foi removido — a fonte
    # canônica do imposto pago no exterior é ForeignTaxPayment (0..N por evento).
    fx_rate = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    amount_brl = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    notes = models.CharField(max_length=500, blank=True)
    # corporate actions: razão do split (de "from" ações para "to" ações;
    # ex.: 1→2 desdobramento, 10→1 grupamento)
    split_ratio_from = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)
    split_ratio_to = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)
    # RF-CST-004: par de pontas de uma transferência de custódia (mesmo UUID)
    transfer_pair_id = models.UUIDField(null=True, blank=True)
    # RF-FTC-009: evento de rendimento cujo imposto retido foi estornado
    refund_of = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="refunds")
    corrects = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="corrected_by")
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["trade_date"]), models.Index(fields=["event_type"])]

    def __str__(self):
        return f"{self.event_type} {self.trade_date} {self.asset or ''} {self.amount_usd}"

    @property
    def foreign_tax_total_usd(self) -> Decimal:
        """Soma dos impostos pagos no exterior (fonte: ForeignTaxPayment)."""
        return sum((p.tax_usd for p in self.foreign_tax_payments.all()), Decimal(0))


JURISDICTION_LEVELS = [("FEDERAL", "Federal"), ("STATE", "Estadual"), ("LOCAL", "Municipal"), ("UNKNOWN", "Desconhecida")]
TAX_TYPES = [("WITHHOLDING_INCOME_TAX", "Retenção na fonte (imposto de renda)"), ("INCOME_TAX", "Imposto de renda"), ("OTHER", "Outro"), ("UNKNOWN", "Desconhecido")]
CAPTURE_METHODS = [("IMPORT", "Importação"), ("MANUAL", "Manual"), ("SYSTEM", "Sistema")]
DATE_EVIDENCE_SOURCES = [
    ("BROKER_STATEMENT", "Extrato da corretora"),
    ("BROKER_TAX_REPORT", "Relatório fiscal da corretora"),
    ("USER_PROVIDED_DOCUMENT", "Documento fornecido pelo usuário"),
    ("OTHER_DOCUMENT", "Outro documento"),
    ("USER_CONFIRMED", "Confirmação do usuário"),
    ("UNKNOWN", "Desconhecida"),
]
# P0 do auditor (Lei 14.754/2023, art. 4º; IN RFB 2.180/2024): o crédito
# aproveitável é o imposto pago em CARÁTER DEFINITIVO — tributo passível de
# restituição/reembolso/compensação no exterior não é definitivo.
RECOVERABILITY_STATUSES = [
    ("NON_RECOVERABLE", "Não recuperável (caráter definitivo)"),
    ("RECOVERABLE", "Recuperável no exterior (restituição/reembolso/compensação)"),
    ("UNKNOWN", "Desconhecida — classifique antes de fechar o ano"),
]


class ForeignTaxPayment(models.Model):
    """Fato documental: imposto pago/retido no exterior vinculado a um evento.

    Registra apenas fatos (país, jurisdição, tipo, valor, data, fonte) — a
    decisão de elegibilidade do crédito fiscal pertence ao motor de crédito.
    A data de pagamento do imposto é independente da data do evento e nunca
    deve ser presumida.
    """

    financial_event = models.ForeignKey(FinancialEvent, on_delete=models.PROTECT, related_name="foreign_tax_payments")
    tax_usd = models.DecimalField(max_digits=20, decimal_places=8)
    foreign_tax_payment_date = models.DateField()
    country_code = models.CharField(max_length=2)
    jurisdiction_level = models.CharField(max_length=16, choices=JURISDICTION_LEVELS)
    tax_type = models.CharField(max_length=32, choices=TAX_TYPES)
    capture_method = models.CharField(max_length=16, choices=CAPTURE_METHODS)
    date_evidence_source = models.CharField(max_length=32, choices=DATE_EVIDENCE_SOURCES)
    recoverability_status = models.CharField(
        max_length=20, choices=RECOVERABILITY_STATUSES, default="UNKNOWN",
    )
    source_document_id = models.CharField(max_length=128, blank=True)
    source_reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.tax_usd is not None and self.tax_usd <= 0:
            raise ValueError("tax_usd do pagamento de imposto no exterior deve ser positivo")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tax_type} {self.country_code} {self.foreign_tax_payment_date} {self.tax_usd}"


class ForeignTaxPaymentAudit(models.Model):
    """Trilha de auditoria da edição do imposto pago no exterior.

    Um registro por edição: diff campo a campo (old/new), motivo obrigatório
    e instante da alteração."""
    payment = models.ForeignKey(ForeignTaxPayment, on_delete=models.PROTECT, related_name="audits")
    changes = models.JSONField()  # [{"field": ..., "old": ..., "new": ...}]
    reason = models.CharField(max_length=255)
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.changed_at:%d/%m/%Y %H:%M} {self.reason}"


class OpeningPosition(models.Model):
    """Posição fiscal de abertura (situação patrimonial em 31/12/2025), com
    custo acumulado em reais já declarado na DIRPF anterior. O motor fiscal
    acompanha apenas os eventos a partir daí (P&R IRPF 2026, ficha Bens e
    Direitos: custo ajustado a cada aplicação, liquidação ou resgate)."""

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="opening_positions")
    account = models.ForeignKey(BrokerAccount, on_delete=models.PROTECT, null=True, blank=True, related_name="opening_positions")
    reference_date = models.DateField(default=date(2025, 12, 31))
    quantity = models.DecimalField(max_digits=24, decimal_places=10)
    total_cost_brl = models.DecimalField(max_digits=20, decimal_places=8)
    notes = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [
            # Auditoria-fiscal 03: uma abertura por conta + ativo + data
            # (aberturas legadas sem conta permanecem permitidas no schema,
            # mas a consulta fiscal é sempre por conta — ver ledger/position.py)
            models.UniqueConstraint(
                fields=["account", "asset", "reference_date"],
                name="uniq_opening_account_asset_date",
            ),
        ]

    @property
    def average_cost_brl(self):
        return self.total_cost_brl / self.quantity if self.quantity else Decimal(0)


class DocumentedBalance(models.Model):
    """Auditoria-fiscal 12: saldo documental da corretora na data-base.

    A reconciliação anual confronta o saldo do ledger e as posições
    calculadas com os saldos documentados (extrato) — divergência ou
    ausência vira pendência, nunca passagem automática."""

    account = models.ForeignKey(BrokerAccount, on_delete=models.PROTECT, related_name="documented_balances")
    reference_date = models.DateField()
    cash_usd = models.DecimalField(max_digits=20, decimal_places=2)
    # posições documentadas em 31/12: [{"ticker": ..., "quantity": ...}]
    positions = models.JSONField(default=list)
    confirmed = models.BooleanField(default=False)
    source_document_id = models.CharField(max_length=128, blank=True)
    source_reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["account", "reference_date"], name="uniq_documented_balance",
        )]

    def __str__(self):
        return f"{self.account} @ {self.reference_date} caixa US$ {self.cash_usd}"


class ImportBatch(models.Model):
    """RF-IMP-002/004: lote de importação de extrato. O hash SHA-256 do
    arquivo garante idempotência (CT-030): mesmo arquivo não reimporta."""

    account = models.ForeignKey(BrokerAccount, on_delete=models.PROTECT, related_name="import_batches")
    source = models.CharField(max_length=32, default="SCHWAB")
    file_hash = models.CharField(max_length=64, unique=True)
    events_created = models.PositiveIntegerField(default=0)
    rows_total = models.PositiveIntegerField(default=0)
    rows_source = models.PositiveIntegerField(default=0)
    rows_imported = models.PositiveIntegerField(default=0)
    rows_unsupported = models.PositiveIntegerField(default=0)
    rows_ignored_confirmed = models.PositiveIntegerField(default=0)
    imported_at = models.DateTimeField(auto_now_add=True)

    @property
    def reconciled(self) -> bool:
        """Auditoria-fiscal 01: linhas do arquivo = importadas + pendências +
        ignoradas com reconhecimento explícito. Nada desaparece sem rastro."""
        return self.rows_source == (
            self.rows_imported + self.rows_unsupported + self.rows_ignored_confirmed
        )

    def __str__(self):
        return f"{self.source} {self.imported_at:%d/%m/%Y %H:%M} (+{self.events_created})"


class ImportIssue(models.Model):
    """Auditoria-fiscal 01: linha de extrato não importada — pendência
    explícita e rastreável. Nenhuma linha do CSV pode desaparecer
    silenciosamente; toda linha não tratada vira um issue PENDING.

    Estados: PENDING → RESOLVED_IMPORTED (lançado manualmente) ou
    RESOLVED_IGNORED (ignorado com justificativa obrigatória)."""

    STATUS_PENDING = "PENDING"
    STATUS_RESOLVED_IMPORTED = "RESOLVED_IMPORTED"
    STATUS_RESOLVED_IGNORED = "RESOLVED_IGNORED"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pendente"),
        (STATUS_RESOLVED_IMPORTED, "Resolvido — lançado manualmente"),
        (STATUS_RESOLVED_IGNORED, "Resolvido — ignorado com justificativa"),
    ]

    batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT, related_name="issues")
    # P1 auditor: RESOLVED_IMPORTED aponta para o lançamento correspondente
    # por FK real (trilha fiscal auditável), não por ID gravado em string.
    resolved_event = models.ForeignKey(
        FinancialEvent, on_delete=models.PROTECT, null=True, blank=True,
        related_name="resolved_import_issues",
    )
    line_number = models.PositiveIntegerField()
    raw_action = models.CharField(max_length=128, blank=True)
    raw_data = models.JSONField(default=dict)
    severity = models.CharField(max_length=16, default="BLOCKING")
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_PENDING)
    resolution = models.CharField(max_length=255, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["batch", "line_number"]

    def _aberta_para_resolucao(self) -> bool:
        """Achado P1 do auditor (17): RESOLVED_IMPORTED cujo evento
        vinculado foi corrigido (desativado) volta a ser pendência — a
        regra é computada, o status gravado não é mutado."""
        return self.status == self.STATUS_PENDING or (
            self.status == self.STATUS_RESOLVED_IMPORTED
            and (self.resolved_event_id is None or not self.resolved_event.active)
        )

    @property
    def esta_aberta(self) -> bool:
        return self._aberta_para_resolucao()

    def resolve_imported(self, event) -> None:
        """P1 auditor: toda pendência resolúvel pela aplicação — vincular o
        evento correspondente (mesma conta do lote, ativo) nunca exige SQL
        manual. Evento desativado/corrigido não é lançamento fiscal válido.
        Achado P1 do auditor (17): pendência cujo evento vinculado foi
        desativado pode ser re-vinculada ao evento substituto."""
        if not self._aberta_para_resolucao():
            raise ValueError(f"Pendência #{self.pk} já está resolvida ({self.status}).")
        if not event.active:
            raise ValueError("O evento vinculado deve estar ativo.")
        if event.account_id != self.batch.account_id:
            raise ValueError(
                "O evento vinculado deve pertencer à mesma conta do lote de importação."
            )
        anterior = self.resolved_event_id
        self.resolved_event = event
        self.status = self.STATUS_RESOLVED_IMPORTED
        self.resolution = (
            f"Evento #{event.pk} vinculado (re-vinculação; substitui #{anterior})"
            if anterior else f"Evento #{event.pk} vinculado"
        )
        self.resolved_at = timezone.now()
        self.save()

    def resolve_ignored(self, reason: str) -> None:
        """Ignorar exige justificativa registrada (nada some sem rastro).
        Achado P1 do auditor (17): pendência reaberta (evento vinculado
        desativado) também pode ser ignorada com justificativa."""
        if not self._aberta_para_resolucao():
            raise ValueError(f"Pendência #{self.pk} já está resolvida ({self.status}).")
        motivo = (reason or "").strip()
        if not motivo:
            raise ValueError("Justificativa é obrigatória para ignorar a pendência.")
        self.status = self.STATUS_RESOLVED_IGNORED
        self.resolution = motivo
        self.resolved_at = timezone.now()
        self.save()

    def __str__(self):
        return f"Issue #{self.pk} lote {self.batch_id} linha {self.line_number} ({self.status})"
