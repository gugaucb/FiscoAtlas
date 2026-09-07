from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from fiscal.models import TaxRule
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(db, residente):
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, effective_from="2026-01-01", effective_until="2026-12-31",
    )
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(account=acct, event_type="APORTE", trade_date=date(2026, 1, 2), amount_usd=Decimal(5000)))
        EventService().record(dict(account=acct, event_type="BUY", asset=asset, trade_date=date(2026, 1, 3), quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(1)))
        EventService().record(dict(account=acct, event_type="SELL", asset=asset, trade_date=date(2026, 6, 1), quantity=Decimal(10), price_usd=Decimal(110), fee_usd=Decimal(1)))
        EventService().record(dict(account=acct, event_type="DIVIDEND", asset=asset, trade_date=date(2026, 6, 15), quantity=Decimal(10), per_share_usd=Decimal(1), tax_usd=Decimal(1), foreign_tax_payment_date=date(2026, 6, 15), date_evidence_source="BROKER_STATEMENT", country_code="US", jurisdiction_level="FEDERAL"))
    return acct, asset


def test_assessment_page_shows_numbers(client, setup):
    # imposto pago no exterior: PTAX COMPRA mockada (mesma taxa do cenário)
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        html = client.get("/apuracao/2026/").content.decode()
    assert "76,00" in html  # imposto devido (pt-br)
    assert "540,00" in html  # renda
    assert "AAPL" in html  # memória de cálculo


def test_assessment_nav_link(client, setup):
    assert "/apuracao/2026/" in client.get("/").content.decode()
