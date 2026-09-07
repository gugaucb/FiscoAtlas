"""Ticket 09 (roadmap-compliance) — Withholding Refund (RF-FTC-009, CT-008).

Estorno de imposto retido no exterior: reduz o crédito aproveitado do ano
(credito baseado na retenção efetivamente paga). Refund em ano posterior ao
fechamento → alerta bloqueante de retificação da DAA do ano de origem.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from fiscal.engine import TaxEngine
from fiscal.models import TaxRule
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def ambiente(residente, db):
    for ano in (2026, 2027):
        TaxRule.objects.create(
            tax_year=ano, rule_version="V2",
            brackets=[{"limit_brl": None, "rate": "0.15"}],
            confirmed=True, quote_type="VENDA", date_rule="INCOME_RECEIPT_DATE",
            effective_from=date(ano, 1, 1),
        )
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="REIT")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        dividendo = EventService().record(dict(
            event_type="DIVIDEND", account=conta, asset=aapl,
            trade_date=date(2026, 3, 1), quantity=Decimal(100),
            per_share_usd=Decimal(1), tax_usd=Decimal(10),
            foreign_tax_payment_date=date(2026, 3, 1), confirm_same_day=False,
            date_evidence_source="BROKER_STATEMENT", country_code="US",
            jurisdiction_level="FEDERAL", tax_type="WITHHOLDING_INCOME_TAX",
        ))
    return conta, aapl, dividendo


def _refund(conta, dividendo, amount, dia):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(dict(
            event_type="WITHHOLDING_REFUND", account=conta, trade_date=dia,
            amount_usd=amount, refund_of=dividendo,
            notes="1042-S: reclassificação de proventos",
        ))


def test_refund_mesmo_ano_estorna_credito(ambiente):
    conta, aapl, dividendo = ambiente
    # sem refund: crédito = 50 BRL (10 × 5)
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        antes = TaxEngine(2026).compute()
    assert antes["withholding_credit_brl"] == Decimal(50)

    _refund(conta, dividendo, Decimal(10), date(2026, 6, 1))
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        depois = TaxEngine(2026).compute()
    # retenção efetiva = 10 − 10 = 0 → crédito 0; rendimento bruto inalterado
    assert depois["withholding_credit_brl"] == Decimal(0)
    assert depois["income_brl"] == antes["income_brl"] == Decimal(500)
    assert depois["tax_due_brl"] == Decimal("75.00")  # 500 × 15%


def test_refund_parcial_reduz_credito_proporcional(ambiente):
    conta, aapl, dividendo = ambiente
    _refund(conta, dividendo, Decimal(4), date(2026, 6, 1))
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        resultado = TaxEngine(2026).compute()
    assert resultado["withholding_credit_brl"] == Decimal(30)  # (10−4) × 5


def test_refund_exige_evento_de_origem(ambiente):
    conta, _, _ = ambiente
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        with pytest.raises(ValueError, match="origem"):
            EventService().record(dict(
                event_type="WITHHOLDING_REFUND", account=conta,
                trade_date=date(2026, 6, 1), amount_usd=Decimal(10),
            ))


def test_refund_ano_subsequente_bloqueia_fechamento(ambiente):
    conta, aapl, dividendo = ambiente
    # fecha 2026 com o crédito aproveitado
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        TaxEngine(2026).save_snapshot(2026)
    _refund(conta, dividendo, Decimal(10), date(2027, 2, 1))
    from fiscal.validator import AnnualClosingValidator
    with pytest.raises(Exception, match="(?i)retifica"):
        AnnualClosingValidator(2027).validate_or_raise()


def test_refund_no_mesmo_ano_nao_bloqueia(ambiente):
    conta, aapl, dividendo = ambiente
    _refund(conta, dividendo, Decimal(10), date(2026, 6, 1))
    from fiscal.validator import AnnualClosingValidator
    AnnualClosingValidator(2026).validate_or_raise()  # não levanta
