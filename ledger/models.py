from datetime import date

from django.db import models

ASSET_TYPES = [("STOCK", "Ação"), ("ETF", "ETF"), ("REIT", "REIT"), ("BOND", "Bond"), ("FUND", "Fundo"), ("OTHER", "Outro")]
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
]


class Asset(models.Model):
    ticker = models.CharField(max_length=32, unique=True)
    description = models.CharField(max_length=255)
    asset_type = models.CharField(max_length=10, choices=ASSET_TYPES)
    isin = models.CharField(max_length=12, null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    country_code = models.CharField(max_length=2, default="US")
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.ticker


class BrokerAccount(models.Model):
    name = models.CharField("apelido do caixa", max_length=128, blank=True)
    broker_name = models.CharField(max_length=128)
    account_number = models.CharField(max_length=64)
    country_code = models.CharField(max_length=2, default="US")
    currency = models.CharField(max_length=3, default="USD")
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES, default="CASH")
    is_interest_bearing = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name or f"{self.broker_name} ({self.account_number})"


class FinancialEvent(models.Model):
    event_type = models.CharField(max_length=16, choices=EVENT_TYPES)
    account = models.ForeignKey(BrokerAccount, on_delete=models.PROTECT, related_name="events")
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, null=True, blank=True, related_name="events")
    trade_date = models.DateField()
    settle_date = models.DateField(null=True, blank=True)
    quantity = models.DecimalField(max_digits=24, decimal_places=10, null=True, blank=True)
    price_usd = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    fee_usd = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    amount_usd = models.DecimalField(max_digits=20, decimal_places=8)
    # DEPRECATED: fonte canônica do imposto é ForeignTaxPayment (0..N por evento).
    # Mantido durante a transição; remoção no ticket 03 (engine/relatório/memória).
    tax_usd = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    fx_rate = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    amount_brl = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    notes = models.CharField(max_length=500, blank=True)
    corrects = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="corrected_by")
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["trade_date"]), models.Index(fields=["event_type"])]

    def __str__(self):
        return f"{self.event_type} {self.trade_date} {self.asset or ''} {self.amount_usd}"


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

    @property
    def average_cost_brl(self):
        return self.total_cost_brl / self.quantity if self.quantity else Decimal(0)
