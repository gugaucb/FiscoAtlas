from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from fiscal.engine import TaxEngine
from fiscal.models import TaxRule
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")


@pytest.fixture
def setup(db, residente):
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, effective_from="2026-01-01", effective_until="2026-12-31",
    )
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    return acct, asset


def _record(acct, **kw):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(dict(account=acct, **kw))


def _compute(engine):
    # imposto pago no exterior: PTAX COMPRA mockada (mesma taxa VENDA do cenário)
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        return engine.compute()


@pytest.mark.django_db
def test_full_year_computation(setup):
    acct, asset = setup
    _record(acct, event_type="APORTE", trade_date=date(2026, 1, 2), amount_usd=Decimal(5000))
    _record(acct, event_type="BUY", asset=asset, trade_date=date(2026, 1, 3),
            quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(1))
    _record(acct, event_type="SELL", asset=asset, trade_date=date(2026, 6, 1),
            quantity=Decimal(10), price_usd=Decimal(110), fee_usd=Decimal(1))
    _record(acct, event_type="DIVIDEND", asset=asset, trade_date=date(2026, 6, 15),
            quantity=Decimal(10), per_share_usd=Decimal(1), tax_usd=Decimal(1),
            foreign_tax_payment_date=date(2026, 6, 15), date_evidence_source="BROKER_STATEMENT", country_code="US", jurisdiction_level="FEDERAL")
    result = _compute(TaxEngine(2026))
    # ganho venda: 10*110-1 = 1099 - custo 1001 (fee compõe custo) = 98 USD = 490 BRL
    # dividendo bruto: 10 USD = 50 BRL → renda 540 BRL
    assert result["income_brl"] == Decimal("540.00")
    assert result["withholding_credit_brl"] == Decimal("5.00")
    assert result["tax_brl"] == Decimal("81.00")
    assert result["tax_due_brl"] == Decimal("76.00")


@pytest.mark.django_db
def test_loss_generates_carryforward(setup):
    acct, asset = setup
    _record(acct, event_type="APORTE", trade_date=date(2026, 1, 2), amount_usd=Decimal(5000))
    _record(acct, event_type="BUY", asset=asset, trade_date=date(2026, 1, 3),
            quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(0))
    _record(acct, event_type="SELL", asset=asset, trade_date=date(2026, 6, 1),
            quantity=Decimal(10), price_usd=Decimal(80), fee_usd=Decimal(0))
    result = _compute(TaxEngine(2026))
    assert result["taxable_brl"] == Decimal("0")
    assert result["loss_carryforward_brl"] == Decimal("1000.00")
    assert result["tax_due_brl"] == Decimal("0")
