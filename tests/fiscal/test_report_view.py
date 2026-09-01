from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from fiscal.models import TaxRule
from fx.service import PtaxService
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(db):
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, effective_from="2026-01-01", effective_until="2026-12-31",
    )
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="123")
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="STOCK")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(account=acct, event_type="APORTE", trade_date=date(2026, 1, 2), amount_usd=Decimal(5000)))
        EventService().record(dict(account=acct, event_type="BUY", asset=asset, trade_date=date(2026, 1, 3), quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(1)))
    return acct


def test_report_page_html(client, setup):
    with mock.patch.object(PtaxService, "get_rate") as get_rate:
        get_rate.return_value = mock.Mock(rate=RATE, effective_date=date(2026, 12, 31))
        html = client.get("/relatorio/2026/").content.decode()
    assert "Bens e Direitos" in html
    assert "AAPL" in html
    assert "/relatorio/2026/pdf" in html


def test_report_pdf_download(client, setup):
    with mock.patch.object(PtaxService, "get_rate") as get_rate:
        get_rate.return_value = mock.Mock(rate=RATE, effective_date=date(2026, 12, 31))
        resp = client.get("/relatorio/2026/pdf")
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"
    assert resp["Content-Type"] == "application/pdf"
