from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from fiscal.models import TaxRule
from fiscal.engine import TaxEngine
from fiscal.report import ReportService
from ledger.models import Asset, BrokerAccount, OpeningPosition
from ledger.position import PositionService
from ledger.service import EventService
from fx.service import PtaxService

RATE = Decimal("5.00000000")


@pytest.fixture
def acct_asset(db, residente):
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, effective_from="2026-01-01", effective_until="2026-12-31",
    )
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    return acct, asset


@pytest.mark.django_db
def test_position_includes_opening_position(acct_asset):
    acct, asset = acct_asset
    OpeningPosition.objects.create(
        asset=asset, reference_date=date(2025, 12, 31),
        quantity=Decimal(100), total_cost_brl=Decimal(95000),
    )
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(account=acct, event_type="BUY", asset=asset,
                                   trade_date=date(2026, 1, 5), quantity=Decimal(10),
                                   price_usd=Decimal(100), fee_usd=Decimal(0)))
    pos = PositionService().position(acct, asset, until=date(2026, 12, 31))
    assert pos["quantity"] == Decimal(110)
    assert pos["cost_brl_total"] == Decimal(100000)  # 95000 + 5000


@pytest.mark.django_db
def test_sell_of_opening_position_uses_opening_cost(acct_asset):
    acct, asset = acct_asset
    OpeningPosition.objects.create(
        asset=asset, reference_date=date(2025, 12, 31),
        quantity=Decimal(100), total_cost_brl=Decimal(95000),
    )
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(account=acct, event_type="SELL", asset=asset,
                                   trade_date=date(2026, 6, 1), quantity=Decimal(10),
                                   price_usd=Decimal(110), fee_usd=Decimal(0)))
    r = PositionService().realized(acct, asset)[0]
    # alienação BRL = 10*110*5 = 5500; custo baixado = 10 × 950 = 9500 → prejuízo 4000
    assert r["gain_brl"] == Decimal("-4000.00")
    result = TaxEngine(2026).compute()
    assert result["loss_carryforward_brl"] == Decimal("4000.00")


@pytest.mark.django_db
def test_report_includes_opening_position_in_assets(acct_asset):
    acct, asset = acct_asset
    OpeningPosition.objects.create(
        asset=asset, reference_date=date(2025, 12, 31),
        quantity=Decimal(100), total_cost_brl=Decimal(95000),
    )
    with mock.patch.object(PtaxService, "get_rate") as get_rate:
        get_rate.return_value = mock.Mock(rate=RATE, effective_date=date(2026, 12, 31))
        report = ReportService(2026).build()
    a = [x for x in report["assets"] if x["ticker"] == "AAPL"]
    assert len(a) == 1
    assert a[0]["quantity"] == Decimal(100)
    assert a[0]["cost_brl_total"] == Decimal(95000)
