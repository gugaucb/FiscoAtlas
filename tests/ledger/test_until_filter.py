from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from ledger.cash import CashLedgerService
from ledger.models import Asset, BrokerAccount
from ledger.position import PositionService
from ledger.service import EventService

RATE = Decimal("5.00000000")


@pytest.fixture
def acct_asset(db):
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    return acct, asset


def _record(acct, **kw):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(dict(account=acct, **kw))


@pytest.mark.django_db
def test_position_until_excludes_later_buys(acct_asset):
    acct, asset = acct_asset
    _record(acct, event_type="BUY", asset=asset, trade_date=date(2026, 1, 5), quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(0))
    _record(acct, event_type="BUY", asset=asset, trade_date=date(2026, 12, 20), quantity=Decimal(5), price_usd=Decimal(100), fee_usd=Decimal(0))
    pos = PositionService().position(acct, asset, until=date(2026, 12, 31))
    assert pos["quantity"] == Decimal(15)
    pos_jun = PositionService().position(acct, asset, until=date(2026, 6, 30))
    assert pos_jun["quantity"] == Decimal(10)


@pytest.mark.django_db
def test_cash_until(acct_asset):
    acct = acct_asset[0]
    _record(acct, event_type="APORTE", trade_date=date(2026, 1, 2), amount_usd=Decimal(5000))
    _record(acct, event_type="APORTE", trade_date=date(2026, 12, 31), amount_usd=Decimal(1000))
    assert CashLedgerService().balance(acct, until=date(2026, 6, 30)) == Decimal(5000)
