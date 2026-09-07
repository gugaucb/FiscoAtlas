"""Resultado da venda em BRL: alienação BRL (PTAX venda) - custo baixado BRL (PTAX compra).

Lei 14.754/2023 / P&R IRPF 2026: a variação cambial integra o rendimento —
o custo NÃO pode ser convertido pela PTAX da data da venda.
"""
from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from fiscal.models import TaxRule
from fiscal.engine import TaxEngine
from ledger.models import Asset, BrokerAccount
from ledger.position import PositionService
from ledger.service import EventService

BUY_FX = Decimal("5.00000000")   # PTAX na compra
SELL_FX = Decimal("6.00000000")  # PTAX na venda (dólar subiu)


@pytest.fixture
def acct_asset(db):
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, effective_from="2026-01-01", effective_until="2026-12-31",
    )
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    return acct, asset


@pytest.mark.django_db
def test_realized_gain_brl_uses_buy_date_fx_for_cost(acct_asset):
    acct, asset = acct_asset
    with mock.patch.object(EventService, "_ptax_rate", return_value=BUY_FX):
        EventService().record(dict(account=acct, event_type="BUY", asset=asset,
                                   trade_date=date(2026, 1, 5), quantity=Decimal(10),
                                   price_usd=Decimal(100), fee_usd=Decimal(0)))
    with mock.patch.object(EventService, "_ptax_rate", return_value=SELL_FX):
        sell = EventService().record(dict(account=acct, event_type="SELL", asset=asset,
                                          trade_date=date(2026, 6, 1), quantity=Decimal(10),
                                          price_usd=Decimal(110), fee_usd=Decimal(0)))
    r = PositionService().realized(acct, asset)[0]
    # alienação BRL = 10*110*6 = 6600; custo baixado BRL = 10*100*5 = 5000 → 1600
    assert r["gain_brl"] == Decimal("1600.00")


@pytest.mark.django_db
def test_tax_engine_uses_brl_result(acct_asset):
    acct, asset = acct_asset
    with mock.patch.object(EventService, "_ptax_rate", return_value=BUY_FX):
        EventService().record(dict(account=acct, event_type="BUY", asset=asset,
                                   trade_date=date(2026, 1, 5), quantity=Decimal(10),
                                   price_usd=Decimal(100), fee_usd=Decimal(0)))
    with mock.patch.object(EventService, "_ptax_rate", return_value=SELL_FX):
        EventService().record(dict(account=acct, event_type="SELL", asset=asset,
                                   trade_date=date(2026, 6, 1), quantity=Decimal(10),
                                   price_usd=Decimal(110), fee_usd=Decimal(0)))
    result = TaxEngine(2026).compute()
    assert result["income_brl"] == Decimal("1600.00")
    assert result["tax_due_brl"] == Decimal("240.00")
