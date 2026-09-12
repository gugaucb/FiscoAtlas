"""Guarda de ano fechado (ticket 25, P0 do auditor).

Existindo AnnualAssessment(year=X, confirmed=True), nenhuma operação que
altere fatos fiscais de X pode ocorrer até a reabertura explícita do ano
(ReopenYearView). O ano fiscal segue a MESMA semântica do engine
(auditoria-fiscal 10): SELL/CASH_IN_LIEU/demais → trade_date;
DIVIDEND/JUROS → income_receipt_date. Correções validam os DOIS anos
fiscais (evento original e corrigido): mover fatos de um ano fechado para
outro também altera história fechada.
"""
from django.core.exceptions import ValidationError

TIPOS_POR_RECEBIMENTO = ("DIVIDEND", "JUROS")


def ano_fiscal_de(event_type: str, trade_date, income_receipt_date) -> int:
    """Ano fiscal do fato, pela mesma semântica do TaxEngine."""
    if event_type in TIPOS_POR_RECEBIMENTO:
        return (income_receipt_date or trade_date).year
    return trade_date.year


def assert_fiscal_year_open(year: int) -> None:
    from fiscal.models import AnnualAssessment
    if AnnualAssessment.objects.filter(year=year, confirmed=True).exists():
        raise ValidationError(
            f"O ano-calendário {year} está fechado (snapshot confirmado). "
            f"Reabra o ano em /apuracao/{year}/ antes de alterar fatos "
            "fiscais dele."
        )


def assert_evento_em_ano_aberto(evento) -> None:
    """Guarda para mutações em evento já persistido (desativação, edição)."""
    assert_fiscal_year_open(
        ano_fiscal_de(
            evento.event_type, evento.trade_date, evento.income_receipt_date,
        )
    )