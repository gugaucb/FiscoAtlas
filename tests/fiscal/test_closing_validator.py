"""Ticket 05 (roadmap-compliance) — Validador bloqueante de fechamento anual.

RF-VAL-001..020: o fechamento (`AnnualAssessment.confirmed = True`) só pode
ocorrer se as precondições fiscais do ano estiverem íntegras. Violações são
coletadas e apresentadas juntas com mensagens explicativas.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from django.core.exceptions import ValidationError

from fiscal.engine import TaxEngine
from fiscal.models import AnnualAssessment, TaxRule
from fiscal.validator import AnnualClosingValidator
from ledger.models import Asset, BrokerAccount, FinancialEvent, ForeignTaxPayment
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def ambiente(residente, db):
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, quote_type="VENDA", date_rule="INCOME_RECEIPT_DATE",
        effective_from=date(2026, 1, 1),
    )
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="1", is_interest_bearing=True)
    return conta


def _compra(conta, ticker="AAPL", qty=Decimal(10), price=Decimal(100), dia=date(2026, 1, 5)):
    asset = Asset.objects.get_or_create(
        ticker=ticker, defaults={"description": ticker, "asset_type": "FOREIGN_EQUITY"}
    )[0]
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(dict(
            event_type="BUY", account=conta, asset=asset, trade_date=dia,
            quantity=qty, price_usd=price, fee_usd=Decimal(0),
        ))


def _dividendo_com_imposto(conta, tax_usd=Decimal(10), per_share=Decimal(1)):
    asset = Asset.objects.get_or_create(
        ticker="AAPL", defaults={"description": "Apple", "asset_type": "FOREIGN_EQUITY"}
    )[0]
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        ev = EventService().record(dict(
            event_type="DIVIDEND", account=conta, asset=asset,
            trade_date=date(2026, 3, 1), quantity=Decimal(10),
            per_share_usd=per_share, tax_usd=tax_usd,
            foreign_tax_payment_date=date(2026, 3, 1), confirm_same_day=False,
            date_evidence_source="BROKER_STATEMENT", country_code="US",
            jurisdiction_level="FEDERAL", tax_type="WITHHOLDING_INCOME_TAX",
        ))
    return ev


# ------------------------------------------------- cenário íntegro passa

def test_ano_integro_passa(ambiente):
    conta = ambiente
    _compra(conta)
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="SELL", account=conta, asset=Asset.objects.get(ticker="AAPL"),
            trade_date=date(2026, 6, 1), quantity=Decimal(5), price_usd=Decimal(110),
            fee_usd=Decimal(0),
        ))
    AnnualClosingValidator(2026).validate_or_raise()  # não levanta


# ------------------------------------------------- RF-VAL-001 residência

def test_bloqueia_sem_residencia_confirmada(ambiente):
    from fiscal.models import Profile
    Profile.objects.update(tax_residency_status="UNKNOWN")
    with pytest.raises(ValidationError, match="residente"):
        AnnualClosingValidator(2026).validate_or_raise()


def test_bloqueia_sem_profile(ambiente):
    from fiscal.models import Profile
    Profile.objects.all().delete()
    with pytest.raises(ValidationError, match="residente"):
        AnnualClosingValidator(2026).validate_or_raise()


# ------------------------------------------------- RF-VAL-002 ativo UNKNOWN

def test_bloqueia_ativo_unknown_com_evento(ambiente):
    conta = ambiente
    asset = Asset.objects.create(ticker="XYZ", description="?", asset_type="UNKNOWN")
    FinancialEvent.objects.create(
        event_type="DIVIDEND", account=conta, asset=asset, trade_date=date(2026, 3, 1),
        quantity=Decimal(1), amount_usd=Decimal(1), fx_rate=RATE, amount_brl=Decimal(5),
    )
    with pytest.raises(ValidationError, match="UNKNOWN"):
        AnnualClosingValidator(2026).validate_or_raise()


# ------------------------------------------------- integridade cambial

def test_bloqueia_evento_sem_amount_brl(ambiente):
    conta = ambiente
    ev = _compra(conta)
    FinancialEvent.objects.filter(pk=ev.pk).update(amount_brl=None)
    with pytest.raises(ValidationError, match="amount_brl"):
        AnnualClosingValidator(2026).validate_or_raise()


def test_bloqueia_evento_sem_fx_rate(ambiente):
    conta = ambiente
    ev = _compra(conta)
    FinancialEvent.objects.filter(pk=ev.pk).update(fx_rate=None)
    with pytest.raises(ValidationError, match="fx_rate"):
        AnnualClosingValidator(2026).validate_or_raise()


# ------------------------------------------------- venda a descoberto

def test_bloqueia_venda_acima_da_custodia(ambiente):
    conta = ambiente
    ev = _compra(conta, qty=Decimal(5))
    # venda direta (acima do saldo) — cria evento sem passar pelo service
    FinancialEvent.objects.create(
        event_type="SELL", account=conta, asset=ev.asset, trade_date=date(2026, 6, 1),
        quantity=Decimal(99), price_usd=Decimal(110), amount_usd=Decimal("10890"),
        fx_rate=RATE, amount_brl=Decimal(54450), fee_usd=Decimal(0), tax_usd=Decimal(0),
    )
    with pytest.raises(ValidationError, match="custódia"):
        AnnualClosingValidator(2026).validate_or_raise()


# ------------------------------------------------- crédito > 15% do bruto

def test_bloqueia_imposto_exterior_acima_de_15_porcento(ambiente):
    conta = ambiente
    # bruto = 10 × 1 + 10 = US$ 20; retido US$ 10 = 50% > 15%
    _dividendo_com_imposto(conta, tax_usd=Decimal(10))
    with pytest.raises(ValidationError, match="15%"):
        AnnualClosingValidator(2026).validate_or_raise()


def test_imposto_ate_15_porcento_passa(ambiente):
    conta = ambiente
    # bruto = 10×2 + 2 = US$ 22; retido 2 = 9% ≤ 15%
    _dividendo_com_imposto(conta, tax_usd=Decimal(2), per_share=Decimal(2))
    AnnualClosingValidator(2026).validate_or_raise()  # não levanta


# ------------------------------------------------- carryforward de crédito

def test_bloqueia_carryforward_de_credito_exterior(ambiente):
    """Crédito retido acima do IR devido não é compensável em anos seguintes
    (Lei 14.754/2023): se o imposto estrangeiro exceder o teto do ano, o
    fechamento é bloqueado para revisão documental."""
    conta = ambiente
    # rendimento bruto pequeno com retenção grande: crédito limitado ao IR
    _dividendo_com_imposto(conta, tax_usd=Decimal("2.5"), per_share=Decimal("1"))
    # bruto 35 BRL → IR 5,25; retenção 12,50 BRL > teto 5,25 → excesso
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        resultado = TaxEngine(2026).compute()
    assert resultado["withholding_credit_brl"] < Decimal("12.50")
    with pytest.raises(ValidationError, match="carryforward|teto"):
        AnnualClosingValidator(2026).validate_or_raise()


# ------------------------------------------------- mensagens agregadas

def test_violacoes_sao_agregadas(ambiente):
    conta = ambiente
    _compra(conta)
    FinancialEvent.objects.create(
        event_type="DIVIDEND", account=conta, asset=Asset.objects.get(ticker="AAPL"),
        trade_date=date(2026, 3, 1), quantity=Decimal(1), amount_usd=Decimal(1),
        fx_rate=None, amount_brl=None,
    )
    from fiscal.models import Profile
    Profile.objects.update(tax_residency_status="NON_RESIDENT")
    with pytest.raises(ValidationError) as excinfo:
        AnnualClosingValidator(2026).validate_or_raise()
    msgs = " ".join(excinfo.value.messages)
    assert "residente" in msgs and "amount_brl" in msgs


# ------------------------------------------------- plugado na view

def test_close_year_view_bloqueado(ambiente, client):
    conta = ambiente
    _dividendo_com_imposto(conta, tax_usd=Decimal(10))
    resp = client.post("/apuracao/2026/fechar/")
    assert resp.status_code == 302  # redireciona de volta com mensagens de erro
    assert not AnnualAssessment.objects.filter(year=2026, confirmed=True).exists()


def test_close_year_view_ok(ambiente, client):
    conta = ambiente
    _compra(conta)
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        resp = client.post("/apuracao/2026/fechar/")
    assert resp.status_code == 302
    assert AnnualAssessment.objects.get(year=2026).confirmed
