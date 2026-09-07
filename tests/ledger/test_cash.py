from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from ledger.cash import CashLedgerService
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")


@pytest.fixture
def acct(db):
    return BrokerAccount.objects.create(broker_name="Avenue", account_number="1")


def _record(acct, **kw):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(dict(account=acct, **kw))


@pytest.mark.django_db
def test_balance_with_buy_and_dividend(acct, db):
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    _record(acct, event_type="APORTE", trade_date=date(2026, 1, 2), amount_usd=Decimal(5000))
    _record(acct, event_type="BUY", asset=asset, trade_date=date(2026, 1, 3),
            quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(1))
    _record(acct, event_type="DIVIDEND", asset=asset, trade_date=date(2026, 2, 1),
            quantity=Decimal(10), per_share_usd=Decimal(1), tax_usd=Decimal(1),
            foreign_tax_payment_date=date(2026, 2, 1), date_evidence_source="BROKER_STATEMENT", country_code="US", jurisdiction_level="FEDERAL")
    balance = CashLedgerService().balance(acct)
    assert balance == Decimal(5000) - Decimal(1001) + Decimal(9)


@pytest.mark.django_db
def test_correction_changes_balance(acct, db):
    _record(acct, event_type="APORTE", trade_date=date(2026, 1, 2), amount_usd=Decimal(5000))
    original = _record(acct, event_type="APORTE", trade_date=date(2026, 1, 2), amount_usd=Decimal(5000))
    _record(acct, event_type="APORTE", trade_date=date(2026, 1, 2), amount_usd=Decimal(4000), corrects=original)
    assert CashLedgerService().balance(acct) == Decimal(9000)  # 5000 + 4000


@pytest.mark.django_db
def test_history_cumulative(acct, db):
    _record(acct, event_type="APORTE", trade_date=date(2026, 1, 2), amount_usd=Decimal(5000))
    hist = CashLedgerService().history(acct)
    assert len(hist) == 1
    assert hist[0]["balance"] == Decimal(5000)
