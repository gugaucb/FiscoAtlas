from decimal import Decimal
from unittest import mock
import pytest
from datetime import date
from fiscal.models import Profile, TaxRule
from fiscal.report import ReportService
from fx.service import PtaxService
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


def test_profile_singleton():
    Profile.objects.create(name="Gustavo", cpf="000.000.000-00")
    with pytest.raises(Exception):
        Profile.objects.create(name="dup", cpf="111.111.111-11")


@pytest.fixture
def setup(db):
    TaxRule.objects.create(tax_year=2026, rule_version="V2",
                           brackets=[{"limit_brl": None, "rate": "0.15"}],
                           confirmed=True, effective_from="2026-01-01", effective_until="2026-12-31")
    Profile.objects.create(name="Gustavo", cpf="000.000.000-00")
    acct = BrokerAccount.objects.create(broker_name="Avenue Securities LLC", account_number="123")
    asset = Asset.objects.create(ticker="AAPL", description="Apple Inc.", asset_type="FOREIGN_EQUITY")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(account=acct, event_type="APORTE", trade_date=date(2026, 1, 2), amount_usd=Decimal(5000)))
        EventService().record(dict(account=acct, event_type="BUY", asset=asset, trade_date=date(2026, 1, 3), quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(1)))
    return acct


def test_report_includes_beneficiary(setup):
    with mock.patch.object(PtaxService, "get_rate") as get_rate:
        get_rate.return_value = mock.Mock(rate=RATE, effective_date=date(2026, 12, 31))
        report = ReportService(2026).build()
    assert report["beneficiary"] == {"name": "Gustavo", "cpf": "000.000.000-00"}
    assert report["exercise"] == 2027
