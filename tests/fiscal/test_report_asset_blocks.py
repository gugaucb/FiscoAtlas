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
def setup(db):
    TaxRule.objects.create(tax_year=2026, rule_version="V2",
                           brackets=[{"limit_brl": None, "rate": "0.15"}],
                           confirmed=True, effective_from="2026-01-01", effective_until="2026-12-31")
    acct = BrokerAccount.objects.create(broker_name="Avenue Securities LLC", account_number="123")
    aapl = Asset.objects.create(ticker="AAPL", description="Apple Inc.", asset_type="STOCK")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        # posição 2025: 20 ações, custo 20*90*5 = 9000
        EventService().record(dict(account=acct, event_type="APORTE", trade_date=date(2025, 1, 2), amount_usd=Decimal(5000)))
        EventService().record(dict(account=acct, event_type="BUY", asset=aapl, trade_date=date(2025, 2, 1), quantity=Decimal(20), price_usd=Decimal(90), fee_usd=Decimal(0)))
        # 2026: compra 5 @110 (5*110*5=2750), dividendo com withholding, venda 5 @120
        EventService().record(dict(account=acct, event_type="BUY", asset=aapl, trade_date=date(2026, 2, 1), quantity=Decimal(5), price_usd=Decimal(110), fee_usd=Decimal(0)))
        EventService().record(dict(account=acct, event_type="DIVIDEND", asset=aapl, trade_date=date(2026, 5, 15), quantity=Decimal(25), per_share_usd=Decimal(1), tax_usd=Decimal(5), foreign_tax_payment_date=date(2026, 5, 15), date_evidence_source="BROKER_STATEMENT", country_code="US", jurisdiction_level="FEDERAL"))
        EventService().record(dict(account=acct, event_type="SELL", asset=aapl, trade_date=date(2026, 8, 1), quantity=Decimal(5), price_usd=Decimal(120), fee_usd=Decimal(0)))
    return acct, aapl


def test_report_asset_block(setup):
    acct, aapl = setup
    with mock.patch.object(PtaxService, "get_rate") as get_rate:
        get_rate.return_value = mock.Mock(rate=RATE, effective_date=date(2026, 12, 31))
        report = ReportService(2026).build()
    block = report["assets"][0]
    assert block["ticker"] == "AAPL"
    assert block["grupo_codigo"] == "03/01"
    assert block["country_name"] == "Estados Unidos"
    assert block["country_code_rfb"] == "249"
    assert block["quantity"] == Decimal(20)  # 20+5-5
    # situações
    assert block["prev_cost_brl"] == Decimal(9000)   # 31/12/2025
    assert block["cost_brl_total"] == Decimal(9400)  # 11750 − baixa 5×470 = 2350
    # PTAX média do custo atual: 9400 BRL / 1880 USD = 5,0
    assert block["cost_usd_total"] == Decimal("1880.00")
    assert block["ptax_media"] == Decimal("5.00000000")
    # aplicação financeira por ativo
    assert block["dividends_brl"] == Decimal(125)  # bruto 25 USD
    assert block["withholding_brl"] == Decimal(25)
    # venda 5 @120: alienação 3000, custo baixado 2350 → ganho 650
    assert block["gains_brl"] == Decimal(650)
    assert block["losses_brl"] == Decimal(0)
