from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")


@pytest.fixture
def db_assets(db):
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="STOCK")
    return acct, asset


def _buy(acct, asset, qty=10, price=100, **kw):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(dict(
            event_type="BUY", account=acct, asset=asset, trade_date=date(2026, 3, 10),
            quantity=Decimal(qty), price_usd=Decimal(price), fee_usd=Decimal("1"), **kw,
        ))


@pytest.mark.django_db
def test_buy_computes_amount_and_brl(db_assets):
    acct, asset = db_assets
    ev = _buy(acct, asset)
    assert ev.amount_usd == Decimal("-1001.00000000")  # -(10*100 + 1)
    assert ev.fx_rate == RATE
    assert ev.amount_brl == Decimal("-5005.00000000")


@pytest.mark.django_db
def test_buy_rejects_wrong_amount(db_assets):
    acct, asset = db_assets
    with pytest.raises(ValueError, match="amount"):
        with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
            EventService().record(dict(
                event_type="BUY", account=acct, asset=asset, trade_date=date(2026, 3, 10),
                quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(1),
                amount_usd=Decimal(-999),
            ))


@pytest.mark.django_db
def test_sell_requires_position(db_assets):
    acct, asset = db_assets
    with pytest.raises(ValueError, match="posição"):
        with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
            EventService().record(dict(
                event_type="SELL", account=acct, asset=asset, trade_date=date(2026, 3, 11),
                quantity=Decimal(5), price_usd=Decimal(110), fee_usd=Decimal(1),
            ))


@pytest.mark.django_db
def test_corrections_deactivate_original(db_assets):
    acct, asset = db_assets
    original = _buy(acct, asset)
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        fix = EventService().record(dict(
            event_type="BUY", account=acct, asset=asset, trade_date=date(2026, 3, 10),
            quantity=Decimal(11), price_usd=Decimal(100), fee_usd=Decimal(1),
            corrects=original,
        ))
    original.refresh_from_db()
    assert not original.active and fix.corrects == original


@pytest.mark.django_db
def test_aporte_uses_informed_amount(db_assets):
    acct, asset = db_assets
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        ev = EventService().record(dict(
            event_type="APORTE", account=acct, trade_date=date(2026, 3, 1),
            amount_usd=Decimal(5000),
        ))
    assert ev.amount_usd == Decimal(5000)
    assert ev.amount_brl == Decimal(25000)
