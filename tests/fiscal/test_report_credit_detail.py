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
pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(db, residente):
    TaxRule.objects.create(tax_year=2026, rule_version="V2",
                           brackets=[{"limit_brl": None, "rate": "0.15"}],
                           confirmed=True, effective_from="2026-01-01", effective_until="2026-12-31")
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        # dividendo: bruto 7 USD (35 BRL), IR EUA 2 USD (10 BRL) — limite 15% = 5,25
        EventService().record(dict(account=acct, event_type="DIVIDEND", asset=aapl,
                                   trade_date=date(2026, 5, 15), quantity=Decimal(7),
                                   per_share_usd=Decimal(1), tax_usd=Decimal(2), foreign_tax_payment_date=date(2026, 5, 15), date_evidence_source="BROKER_STATEMENT", country_code="US", jurisdiction_level="FEDERAL"))
    return acct


def test_credito_detalhado_com_limite(setup):
    with mock.patch.object(PtaxService, "get_rate") as get_rate:
        get_rate.return_value = mock.Mock(rate=RATE, effective_date=date(2026, 12, 31))
        report = ReportService(2026).build()
    rows = report["income"]["credit_detail"]
    assert len(rows) == 1
    r = rows[0]
    assert r["gross_brl"] == Decimal("35.00")
    assert r["limit_brl"] == Decimal("5.25")   # 15% × 35
    assert r["withholding_brl"] == Decimal("10.00")
    assert r["credit_used_brl"] == Decimal("5.25")
    assert r["credit_unused_brl"] == Decimal("4.75")  # descartado — sem carryforward


def test_sem_rendimentos_lista_vazia(db, residente):
    TaxRule.objects.create(tax_year=2026, rule_version="V2",
                           brackets=[{"limit_brl": None, "rate": "0.15"}],
                           confirmed=True, effective_from="2026-01-01", effective_until="2026-12-31")
    with mock.patch.object(PtaxService, "get_rate") as get_rate:
        get_rate.return_value = mock.Mock(rate=RATE, effective_date=date(2026, 12, 31))
        report = ReportService(2026).build()
    assert report["income"]["credit_detail"] == []
