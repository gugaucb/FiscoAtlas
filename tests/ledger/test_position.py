from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from ledger.models import Asset, BrokerAccount
from ledger.position import PositionService
from ledger.service import EventService

RATE = Decimal("5.00000000")


@pytest.fixture
def acct_asset(db):
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    return acct, asset


def _record(acct, asset, **kw):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(dict(account=acct, asset=asset, **kw))


@pytest.mark.django_db
def test_average_cost_two_buys(acct_asset):
    acct, asset = acct_asset
    _record(acct, asset, event_type="BUY", trade_date=date(2026, 1, 5), quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(0))
    _record(acct, asset, event_type="BUY", trade_date=date(2026, 2, 5), quantity=Decimal(10), price_usd=Decimal(120), fee_usd=Decimal(0))
    pos = PositionService().position(acct, asset)
    assert pos["quantity"] == Decimal(20)
    assert pos["avg_cost_usd"] == Decimal(110)
    assert pos["cost_brl_total"] == Decimal(20) * Decimal(110) * RATE


@pytest.mark.django_db
def test_sell_reduces_position_keeps_avg_cost(acct_asset):
    acct, asset = acct_asset
    _record(acct, asset, event_type="BUY", trade_date=date(2026, 1, 5), quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(0))
    _record(acct, asset, event_type="SELL", trade_date=date(2026, 2, 5), quantity=Decimal(4), price_usd=Decimal(110), fee_usd=Decimal(1))
    pos = PositionService().position(acct, asset)
    assert pos["quantity"] == Decimal(6)
    assert pos["avg_cost_usd"] == Decimal(100)


@pytest.mark.django_db
def test_correction_changes_position(acct_asset):
    acct, asset = acct_asset
    original = _record(acct, asset, event_type="BUY", trade_date=date(2026, 1, 5), quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(0))
    _record(acct, asset, event_type="BUY", trade_date=date(2026, 1, 5), quantity=Decimal(12), price_usd=Decimal(100), fee_usd=Decimal(0), corrects=original)
    pos = PositionService().position(acct, asset)
    assert pos["quantity"] == Decimal(12)  # original inativo


@pytest.mark.django_db
def test_realized_gain(acct_asset):
    acct, asset = acct_asset
    _record(acct, asset, event_type="BUY", trade_date=date(2026, 1, 5), quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(0))
    _record(acct, asset, event_type="SELL", trade_date=date(2026, 2, 5), quantity=Decimal(4), price_usd=Decimal(110), fee_usd=Decimal(1))
    realized = PositionService().realized(acct, asset)
    assert len(realized) == 1
    r = realized[0]
    assert r["avg_cost_usd"] == Decimal(100)
    assert r["gain_usd"] == Decimal(39)  # 4*110 - 1 - 4*100
