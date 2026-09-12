"""Ticket 30 (P0 do auditor) — ano fechado sem alteração estrutural.

OpeningPosition e campos fiscalmente estruturais de BrokerAccount
(titularidade, is_interest_bearing) não podem alterar anos confirmados
sem reabertura explícita. Campos descritivos permanecem editáveis.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from django.core.exceptions import ValidationError

from fiscal.models import AnnualAssessment
from ledger.models import Asset, BrokerAccount, OpeningPosition

RATE = Decimal("5.00000000")


def _ano_fechado(year):
    AnnualAssessment.objects.create(
        year=year, rule_version="V2", income_brl=0, loss_brl=0, taxable_brl=0,
        tax_brl=0, withholding_credit_brl=0, tax_due_brl=0,
        loss_carryforward_brl=0, confirmed=True,
    )


def _conta(**kwargs):
    return BrokerAccount.objects.create(
        broker_name="Avenue", account_number="1", **kwargs
    )


def _posicao(conta, **kwargs):
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    return OpeningPosition.objects.create(
        account=conta, asset=aapl, quantity=Decimal(100),
        total_cost_brl=Decimal(50000), **kwargs,
    )


# 1) alteração de OpeningPosition bloqueada

@pytest.mark.django_db
def test_alterar_opening_position_bloqueada(db, residente):
    conta = _conta()
    pos = _posicao(conta, reference_date=date(2025, 12, 31))
    _ano_fechado(2026)
    pos.total_cost_brl = Decimal(40000)
    with pytest.raises(ValidationError, match="Reabra o ano 2026"):
        pos.save()
    pos.refresh_from_db()
    assert pos.total_cost_brl == Decimal(50000)  # valor original permanece


@pytest.mark.django_db
def test_criar_opening_position_retroativa_bloqueada(db, residente):
    _ano_fechado(2026)
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    with pytest.raises(ValidationError, match="Reabra o ano 2026"):
        OpeningPosition.objects.create(
            account=_conta(), asset=aapl, reference_date=date(2025, 12, 31),
            quantity=Decimal(100), total_cost_brl=Decimal(50000),
        )


@pytest.mark.django_db
def test_apos_reabrir_alteracao_passa(db, residente):
    conta = _conta()
    pos = _posicao(conta, reference_date=date(2025, 12, 31))
    _ano_fechado(2026)
    AnnualAssessment.objects.filter(year=2026).delete()  # reaberto
    pos.total_cost_brl = Decimal(40000)
    pos.save()
    pos.refresh_from_db()
    assert pos.total_cost_brl == Decimal(40000)


@pytest.mark.django_db
def test_opening_position_futura_nao_bloqueada(db, residente):
    """Abertura em 31/12/2027 não pode afetar 2026 — fechamento de 2026
    não bloqueia."""
    _ano_fechado(2026)
    aapl = Asset.objects.create(ticker="TSLA", description="Tesla", asset_type="FOREIGN_EQUITY")
    OpeningPosition.objects.create(
        account=_conta(), asset=aapl, reference_date=date(2027, 12, 31),
        quantity=Decimal(100), total_cost_brl=Decimal(50000),
    )


# 5) titularidade bloqueada

@pytest.mark.django_db
def test_ownership_share_bloqueado_com_ano_fechado(db, residente):
    conta = _conta()
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    with mock.patch("ledger.service.EventService._ptax_rate", return_value=RATE):
        from ledger.service import EventService
        EventService().record(dict(
            account=conta, event_type="APORTE",
            trade_date=date(2026, 3, 1), amount_usd=Decimal(1000),
        ))
    _ano_fechado(2026)
    conta.ownership_share = Decimal("50.00")
    with pytest.raises(ValidationError, match="Reabra o ano 2026"):
        conta.save()
    conta.refresh_from_db()
    assert conta.ownership_share == Decimal(100)


@pytest.mark.django_db
def test_ownership_share_passa_apos_reabrir(db, residente):
    conta = _conta()
    from ledger.service import EventService
    with mock.patch("ledger.service.EventService._ptax_rate", return_value=RATE):
        EventService().record(dict(
            account=conta, event_type="APORTE",
            trade_date=date(2026, 3, 1), amount_usd=Decimal(1000),
        ))
    _ano_fechado(2026)
    AnnualAssessment.objects.filter(year=2026).delete()
    conta.ownership_share = Decimal("50.00")
    conta.save()
    conta.refresh_from_db()
    assert conta.ownership_share == Decimal("50.00")


# 6) is_interest_bearing fiscalmente relevante (isenção de caixa IN RFB 2180/2024 art. 3º)

@pytest.mark.django_db
def test_is_interest_bearing_bloqueado(db, residente):
    conta = _conta()
    from ledger.service import EventService
    with mock.patch("ledger.service.EventService._ptax_rate", return_value=RATE):
        EventService().record(dict(
            account=conta, event_type="APORTE",
            trade_date=date(2026, 3, 1), amount_usd=Decimal(1000),
        ))
    _ano_fechado(2026)
    conta.is_interest_bearing = True
    with pytest.raises(ValidationError, match="Reabra o ano 2026"):
        conta.save()


# 7) campo descritivo permanece editável

@pytest.mark.django_db
def test_campo_descritivo_editavel_com_ano_fechado(db, residente):
    conta = _conta()
    _ano_fechado(2026)
    conta.name = "Meu apelido"
    conta.save()
    conta.refresh_from_db()
    assert conta.name == "Meu apelido"