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


# --- Ticket 30 (P0 do auditor): guarda ESTRUTURAL de ano fechado ---------
# OpeningPosition e campos fiscalmente estruturais de BrokerAccount
# (ownership_type, ownership_share, is_interest_bearing) não podem alterar
# anos confirmados sem reabertura explícita. Campos descritivos (apelido)
# permanecem editáveis.


def _mensagem_estrutural(ano: int) -> str:
    return (
        f"O ano-calendário {ano} está fechado. Reabra o ano {ano} antes "
        "de alterar dados estruturais que afetam essa apuração."
    )


def assert_no_closed_year_affected_from(reference_date) -> None:
    """Uma posição/estrutura com data-base D pode afetar a apuração de
    qualquer ano-calendário >= D.year. Regra conservadora e simples."""
    from datetime import date as date_cls

    from fiscal.models import AnnualAssessment
    if not isinstance(reference_date, date_cls):
        reference_date = date_cls.fromisoformat(str(reference_date))
    fechado = (
        AnnualAssessment.objects.filter(
            year__gte=reference_date.year, confirmed=True,
        ).order_by("-year").values_list("year", flat=True).first()
    )
    if fechado is not None:
        raise ValidationError(_mensagem_estrutural(fechado))


def anos_fechados_afetados_por_conta(conta) -> list[int]:
    """Anos confirmados em que a conta PARTICIPOU — mesma relevância do
    ticket 27 (evento no ano fiscal, OpeningPosition até a data-base ou
    patrimônio carregado: caixa ≠ 0 / custódia > 0)."""
    from datetime import date

    from fiscal.models import AnnualAssessment
    afetados = []
    for aa in AnnualAssessment.objects.filter(confirmed=True).order_by("year"):
        yearend = date(aa.year, 12, 31)
        tem_evento = any(
            ano_fiscal_de(e.event_type, e.trade_date, e.income_receipt_date) == aa.year
            for e in conta.events.filter(active=True)
        )
        if (
            tem_evento
            or conta.opening_positions.filter(reference_date__lte=yearend).exists()
            or conta.__class__._tem_patrimonio_carregado(conta, yearend)
        ):
            afetados.append(aa.year)
    return afetados


def assert_no_closed_year_affected_for_account(conta) -> None:
    """A política de reabertura é do mais recente para o mais antigo —
    a mensagem indica o ano fechado mais recente atingido."""
    afetados = anos_fechados_afetados_por_conta(conta)
    if afetados:
        raise ValidationError(_mensagem_estrutural(max(afetados)))