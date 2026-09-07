import pytest
from ledger.models import Asset, BrokerAccount, FinancialEvent


@pytest.fixture
def account(db):
    return BrokerAccount.objects.create(broker_name="Avenue", account_number="1")


@pytest.fixture
def asset(db):
    return Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")


def _event(account, asset, **kw):
    base = dict(
        event_type="BUY", account=account, asset=asset, trade_date="2026-03-10",
        quantity=10, price_usd=100, amount_usd=-1000, fee_usd=1,
    )
    base.update(kw)
    return FinancialEvent.objects.create(**base)


@pytest.mark.django_db
def test_buy_event_stores_decimal_fields(account, asset):
    ev = _event(account, asset, quantity=10, price_usd=100.5, amount_usd=-1005)
    assert ev.quantity == 10
    assert ev.price_usd == 100.5
    assert ev.amount_usd == -1005
    assert ev.active


@pytest.mark.django_db
def test_cash_event_has_null_asset(account):
    ev = FinancialEvent.objects.create(
        event_type="APORTE", account=account, trade_date="2026-03-01",
        amount_usd=5000, fee_usd=0,
    )
    assert ev.asset is None
    assert ev.quantity is None
