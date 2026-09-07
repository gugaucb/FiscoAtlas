from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from fiscal.models import TaxRule
from fiscal.report import ReportService
from fx.service import PtaxService
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
    acct = BrokerAccount.objects.create(broker_name="Avenue Securities LLC", account_number="123")
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    msft = Asset.objects.create(ticker="MSFT", description="Microsoft", asset_type="FOREIGN_EQUITY")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(account=acct, event_type="APORTE", trade_date=date(2026, 1, 2), amount_usd=Decimal(5000)))
        EventService().record(dict(account=acct, event_type="BUY", asset=aapl, trade_date=date(2026, 1, 3), quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(1)))
        EventService().record(dict(account=acct, event_type="SELL", asset=aapl, trade_date=date(2026, 6, 1), quantity=Decimal(10), price_usd=Decimal(110), fee_usd=Decimal(1)))
        EventService().record(dict(account=acct, event_type="BUY", asset=msft, trade_date=date(2026, 3, 1), quantity=Decimal(4), price_usd=Decimal(200), fee_usd=Decimal(1)))
    return acct


@pytest.mark.django_db
def test_build_report(setup):
    acct = setup
    with mock.patch.object(PtaxService, "get_rate") as get_rate:
        get_rate.return_value = mock.Mock(rate=RATE, effective_date=date(2026, 12, 31))
        report = ReportService(2026).build()
    assert report["year"] == 2026
    tickers = [a["ticker"] for a in report["assets"]]
    assert tickers == ["MSFT"]  # AAPL posição zero não entra
    assert report["assets"][0]["quantity"] == Decimal(4)
    assert report["cash"][0]["balance_usd"] == Decimal("4297.00000000")
    assert report["cash"][0]["balance_brl"] == Decimal("21485.00000000")
    assert report["income"]["tax_due_brl"] == Decimal("73.50")  # ganho AAPL 98×5=490 × 15%
