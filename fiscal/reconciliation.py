"""Auditoria-fiscal 12 — reconciliação anual (RF-REC-001).

Pergunta do serviço: "os dados de ENTRADA estão completos e conciliados?"
— separado do AnnualClosingValidator (que responde "as regras FISCAIS do
ano estão íntegras?"). O fechamento executa primeiro a reconciliação,
depois a validação fiscal, e só então apura e confirma o snapshot.

Regras: (1) pendência de importação com EVENTO no ano-calendário bloqueia
(o critério é a data do evento, não da pendência); (2) caixa do ledger
confrontado com o saldo documental confirmado na data-base — ausência ou
divergência é pendência, nunca passagem automática; (3) posições em 31/12
confrontadas com as documentadas; (4) rendimento tributável exige estado
declarado do imposto exterior — "sem imposto" não é retenção zero
presumida; (5) revisão pendente de fatos fiscais bloqueia com orientação.
"""
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

from fiscal.date_rules import income_fiscal_year_q
from ledger.cash import CashLedgerService
from ledger.models import Asset, BrokerAccount, DocumentedBalance, FinancialEvent, ImportIssue
from ledger.position import PositionService

TOL = Decimal("0.01")


def _parse_data_documento(raw_data: dict):
    from ledger.importers.base import parse_date_us
    valor = (raw_data or {}).get("Date")
    if not valor:
        return None
    try:
        return parse_date_us(valor)
    except Exception:
        return None


class AnnualReconciliationService:
    def __init__(self, year: int):
        self.year = year
        self.issues: list[str] = []

    def run_or_raise(self):
        self.issues = []
        self._checar_importacoes()
        self._checar_caixa()
        self._checar_posicoes()
        self._checar_estado_imposto_exterior()
        if self.issues:
            raise ValidationError(self.issues)

    # ------------------------------------------------------------ (1) importação
    def _checar_importacoes(self):
        for issue in ImportIssue.objects.filter(status=ImportIssue.STATUS_PENDING).select_related("batch"):
            data_evento = _parse_data_documento(issue.raw_data)
            if data_evento is None or data_evento.year == self.year:
                quando = f"em {data_evento:%d/%m/%Y}" if data_evento else "com data ilegível"
                self.issues.append(
                    f"Pendência de importação: linha {issue.line_number} do lote "
                    f"{issue.batch_id} ('{issue.raw_action or 'ação vazia'}') "
                    f"referente a evento {quando} no ano-calendário {self.year} — "
                    "resolva (lançamento manual ou ignora com justificativa) antes de fechar o ano."
                )

    # ------------------------------------------------------------ (2) caixa
    def _checar_caixa(self):
        data_base = date(self.year, 12, 31)
        for conta in BrokerAccount.objects.filter(active=True):
            if not self._conta_relevante(conta, data_base):
                continue
            documentado = DocumentedBalance.objects.filter(
                account=conta, reference_date=data_base,
            ).first()
            if documentado is None or not documentado.confirmed:
                self.issues.append(
                    f"Saldo documental de {conta} em 31/12/{self.year} não informado "
                    "ou não confirmado — informe o extrato da corretora em "
                    "/documentar-saldos/ antes de fechar o ano (sem passagem automática)."
                )
                continue
            calculado = CashLedgerService().balance(conta, until=data_base).quantize(Decimal("0.01"))
            if abs(calculado - documentado.cash_usd) > TOL:
                self.issues.append(
                    f"Caixa de {conta} em 31/12/{self.year}: ledger US$ {calculado} "
                    f"≠ documentado US$ {documentado.cash_usd} — concilie o extrato "
                    "ou corrija os lançamentos antes de fechar o ano."
                )

    # ------------------------------------------------------------ (3) posições
    def _checar_posicoes(self):
        data_base = date(self.year, 12, 31)
        for conta in BrokerAccount.objects.filter(active=True):
            if not self._conta_relevante(conta, data_base):
                continue
            documentado = DocumentedBalance.objects.filter(
                account=conta, reference_date=data_base,
            ).first()
            if documentado is None or not documentado.confirmed:
                continue  # já reportado em _checar_caixa
            doc_por_ticker = {str(p["ticker"]).upper(): Decimal(str(p["quantity"])) for p in (documentado.positions or [])}
            for asset in Asset.objects.filter(events__account=conta, events__active=True).distinct():
                qty = PositionService().position(conta, asset, until=data_base)["quantity"]
                if qty <= 0 and asset.ticker not in doc_por_ticker:
                    continue
                esperado = doc_por_ticker.get(asset.ticker)
                if esperado is None:
                    self.issues.append(
                        f"Posição de {asset.ticker} em {conta} ({qty} un. em 31/12/{self.year}) "
                        "sem quantidade documentada no extrato — complete em "
                        "/documentar-saldos/ antes de fechar o ano."
                    )
                elif abs(esperado - qty) > TOL:
                    self.issues.append(
                        f"Posição de {asset.ticker} em {conta}: calculada {qty} un. "
                        f"≠ documentada {esperado} em 31/12/{self.year} — concilie antes de fechar."
                    )

    # ------------------------------------------------------------ (4) imposto exterior
    def _checar_estado_imposto_exterior(self):
        rendimentos = FinancialEvent.objects.filter(
            income_fiscal_year_q(self.year), active=True,
        ).select_related("account")
        for ev in rendimentos:
            if ev.foreign_tax_state == "UNDECLARED":
                self.issues.append(
                    f"Rendimento {ev} (id {ev.id}) sem declaração do estado do "
                    "imposto exterior — 'sem imposto' não é retenção zero presumida. "
                    "Declare NO_WITHHOLDING (sem retenção) ou registre o pagamento "
                    "antes de fechar o ano."
                )
            elif ev.foreign_tax_state == "REVIEW_PENDING":
                self.issues.append(
                    f"Rendimento {ev} (id {ev.id}) com imposto exterior PENDENTE DE "
                    "REVISÃO documental — revise e declare antes de fechar o ano."
                )

    def _conta_relevante(self, conta, data_base) -> bool:
        """Só contas com atividade no ano (ou saldo) precisam de reconciliação."""
        return (
            FinancialEvent.objects.filter(
                account=conta, active=True, trade_date__year=self.year,
            ).exists()
            or CashLedgerService().balance(conta, until=data_base) != 0
        )