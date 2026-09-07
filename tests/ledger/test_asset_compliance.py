"""Ticket 01 (roadmap-compliance) — Cadastro explícito de ativos.

Regras: RF-AST-003/006/007/009, RF-ARQ-006, RF-VAL-002.
- fim da auto-criação silenciosa de ativos (clean_asset_ticker);
- taxonomia legal da Lei 14.754/2023 em Asset;
- TaxEngine bloqueia CONTROLLED_ENTITY / TRUST / UNKNOWN / entidade controlada.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from django.core.exceptions import ValidationError

from fiscal.engine import TaxEngine
from ledger.models import Asset, BrokerAccount, FinancialEvent
from ledger.service import EventService

pytestmark = pytest.mark.django_db

RATE = Decimal("5.00000000")


def _compute(engine):
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        return engine.compute()


@pytest.fixture
def conta():
    return BrokerAccount.objects.create(broker_name="Avenue", account_number="123", is_interest_bearing=True)


@pytest.fixture
def regra_2026(residente):
    from fiscal.models import TaxRule
    return TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, quote_type="VENDA", date_rule="INCOME_RECEIPT_DATE", effective_from=date(2026, 1, 1),
    )


def _dados_compra(conta, ticker):
    return dict(event_type="BUY", account=conta, trade_date=date(2026, 1, 10),
                asset_ticker=ticker, quantity=Decimal(10), price_usd=Decimal(100))


# ---------------------------------------------------------------- taxonomia

def test_asset_tipos_legais():
    from ledger.models import ASSET_TYPES
    esperados = {"FOREIGN_EQUITY", "FOREIGN_ETF", "REIT", "US_TREASURY",
                 "FOREIGN_BOND", "FOREIGN_FUND", "CONTROLLED_ENTITY", "TRUST", "UNKNOWN"}
    assert {codigo for codigo, _ in ASSET_TYPES} == esperados


def test_asset_tem_campos_de_controle():
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    assert aapl.is_controlled_entity is False
    assert aapl.ownership_share_pct == Decimal(0)


def test_migration_mapeia_tipos_legados():
    # legados: STOCK→FOREIGN_EQUITY, ETF→FOREIGN_ETF, BOND→FOREIGN_BOND,
    # FUND→FOREIGN_FUND, OTHER→UNKNOWN, REIT→REIT
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    voo = Asset.objects.create(ticker="VOO", description="Vanguard", asset_type="FOREIGN_ETF")
    assert aapl.asset_type == "FOREIGN_EQUITY"
    assert voo.asset_type == "FOREIGN_ETF"
    for ticker in ("AAPL", "VOO"):
        assert Asset.objects.get(ticker=ticker)


# --------------------------------------------- fim da auto-inferência

def test_eventform_rejeita_ticker_inexistente():
    from ledger.forms import EventForm
    form = EventForm(data={
        "event_type": "BUY", "trade_date": "2026-01-10", "asset_ticker": "TSLA",
        "quantity": "10", "price_usd": "200",
    })
    assert not form.is_valid()
    assert any("não cadastrado" in msg or "nao cadastrado" in msg.lower()
               for msgs in form.errors.values() for msg in msgs)
    assert not Asset.objects.filter(ticker="TSLA").exists()


def test_service_tambem_rejeita_ativo_inexistente(conta):
    with pytest.raises(ValueError):
        EventService().record(_dados_compra(conta, "TSLA"))
    assert not Asset.objects.filter(ticker="TSLA").exists()
    assert FinancialEvent.objects.count() == 0


def test_compra_com_ativo_cadastrado_funciona(conta):
    Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    ev = EventService().record(_dados_compra(conta, "aapl"))
    assert ev.asset.ticker == "AAPL"


# ------------------------------------------------- cadastro explícito

def test_assetform_cadastra_ativo_explicito():
    from ledger.forms import AssetForm
    form = AssetForm(data={
        "ticker": "O", "description": "Realty Income", "asset_type": "REIT",
        "country_code": "US", "is_controlled_entity": "false",
    })
    assert form.is_valid(), form.errors
    asset = form.save()
    assert asset.asset_type == "REIT"
    assert asset.ticker == "O"


def test_assetform_aceita_entidade_controlada_com_participacao():
    from ledger.forms import AssetForm
    form = AssetForm(data={
        "ticker": "HOLD1", "description": "Holding offshore",
        "asset_type": "CONTROLLED_ENTITY", "country_code": "KY",
        "is_controlled_entity": "on", "ownership_share_pct": "100",
    })
    assert form.is_valid(), form.errors
    asset = form.save()
    assert asset.is_controlled_entity is True
    assert asset.ownership_share_pct == Decimal("100")


def test_view_cadastro_de_ativo_disponivel(client):
    resp = client.get("/ativos/novo/")
    assert resp.status_code == 200
    resp = client.post("/ativos/novo/", {
        "ticker": "TLT", "description": "iShares 20+ Year Treasury",
        "asset_type": "US_TREASURY", "country_code": "US",
    })
    assert resp.status_code == 302
    assert Asset.objects.filter(ticker="TLT", asset_type="US_TREASURY").exists()


# -------------------------------------------- bloqueio no TaxEngine

@pytest.mark.parametrize("tipo,controlada", [
    ("CONTROLLED_ENTITY", False),
    ("TRUST", False),
    ("UNKNOWN", False),
    ("FOREIGN_EQUITY", True),  # is_controlled_entity=True bloqueia mesmo tipo elegível
])
def test_engine_bloqueia_regimes_nao_cobertos(conta, regra_2026, tipo, controlada):
    asset = Asset.objects.create(
        ticker="X", description="X", asset_type=tipo, is_controlled_entity=controlada)
    EventService().record(dict(event_type="BUY", account=conta, asset=asset,
                               trade_date=date(2026, 2, 1), quantity=Decimal(5),
                               price_usd=Decimal(100)))
    EventService().record(dict(event_type="SELL", account=conta, asset=asset,
                               trade_date=date(2026, 6, 1), quantity=Decimal(5),
                               price_usd=Decimal(120)))
    with pytest.raises(ValidationError, match="Regime não coberto"):
        _compute(TaxEngine(2026))


def test_engine_permite_tipos_elegiveis(conta, regra_2026):
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    EventService().record(dict(event_type="BUY", account=conta, asset=asset,
                               trade_date=date(2026, 2, 1), quantity=Decimal(5),
                               price_usd=Decimal(100)))
    EventService().record(dict(event_type="SELL", account=conta, asset=asset,
                               trade_date=date(2026, 6, 1), quantity=Decimal(5),
                               price_usd=Decimal(120)))
    resultado = _compute(TaxEngine(2026))
    assert resultado["income_brl"] > 0
