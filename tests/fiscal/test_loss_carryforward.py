from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from fiscal.engine import TaxEngine
from fiscal.models import TaxRule
from fiscal.report import ReportService
from fx.service import PtaxService
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def rules(db, residente):
    for year in (2025, 2026):
        TaxRule.objects.create(tax_year=year, rule_version="V2",
                               brackets=[{"limit_brl": None, "rate": "0.15"}],
                               confirmed=True,
                               effective_from=f"{year}-01-01", effective_until=f"{year}-12-31")


def _account():
    return BrokerAccount.objects.create(broker_name="Avenue", account_number="1")


def test_prejuizo_herdado_do_ano_anterior(rules):
    acct = _account()
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        # 2025: compra 10 @100 (5000 BRL), vende 10 @80 (4000 BRL) → prejuízo 1000 BRL
        EventService().record(dict(account=acct, event_type="BUY", asset=aapl,
                                   trade_date=date(2025, 1, 5), quantity=Decimal(10), price_usd=Decimal(100)))
        EventService().record(dict(account=acct, event_type="SELL", asset=aapl,
                                   trade_date=date(2025, 6, 5), quantity=Decimal(10), price_usd=Decimal(80)))
        # 2026: ganho 200 BRL (vende 5 @104)
        EventService().record(dict(account=acct, event_type="BUY", asset=aapl,
                                   trade_date=date(2026, 1, 5), quantity=Decimal(5), price_usd=Decimal(100)))
        EventService().record(dict(account=acct, event_type="SELL", asset=aapl,
                                   trade_date=date(2026, 6, 5), quantity=Decimal(5), price_usd=Decimal(104)))
    r2025 = TaxEngine(2025).compute()
    assert r2025["loss_carryforward_brl"] == Decimal("1000.00")
    TaxEngine.save_snapshot(2025)

    r2026 = TaxEngine(2026).compute()
    # 2026: ganho 100 (5×4 USD×5) + herdado 1000 = 1100 de prejuízo disponível
    assert r2026["loss_inherited_brl"] == Decimal("1000.00")
    assert r2026["income_brl"] == Decimal("100.00")
    # compensa integralmente: base 0, imposto 0, saldo a compensar 900
    assert r2026["taxable_brl"] == Decimal("0.00")
    assert r2026["tax_due_brl"] == Decimal("0.00")
    assert r2026["loss_carryforward_brl"] == Decimal("900.00")
    kinds = [d["kind"] for d in r2026["detail"]]
    assert "loss_carryforward" in kinds


def test_sem_ano_anterior_nao_herde(rules):
    _account()
    r2026 = TaxEngine(2026).compute()
    assert r2026["loss_inherited_brl"] == Decimal("0.00")


def test_relatorio_mostra_reconciliacao(rules):
    acct = _account()
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(account=acct, event_type="BUY", asset=aapl,
                                   trade_date=date(2025, 1, 5), quantity=Decimal(10), price_usd=Decimal(100)))
        EventService().record(dict(account=acct, event_type="SELL", asset=aapl,
                                   trade_date=date(2025, 6, 5), quantity=Decimal(10), price_usd=Decimal(80)))
    TaxEngine.save_snapshot(2025)
    with mock.patch.object(PtaxService, "get_rate") as get_rate:
        get_rate.return_value = mock.Mock(rate=RATE, effective_date=date(2026, 12, 31))
        report = ReportService(2026).build()
    inc = report["income"]
    assert inc["loss_inherited_brl"] == Decimal("1000.00")
    assert inc["loss_carryforward_brl"] == Decimal("1000.00")
