"""Ticket 04 (roadmap-compliance) — Corporate actions: splits, reverse splits e cash-in-lieu.

Regras (RF-CA-001..003, CT-016, CT-017): o split altera quantidade e reduz o
custo unitário médio; o CUSTO TOTAL HISTÓRICO EM BRL PERMANECE INALTERADO.
Cash-in-lieu de fração gera baixa de custo e apuração de alienação proporcional.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from fiscal.engine import TaxEngine
from fiscal.models import TaxRule
from ledger.models import Asset, BrokerAccount
from ledger.position import PositionService
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(residente, db):
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, quote_type="VENDA", date_rule="INCOME_RECEIPT_DATE",
        effective_from=date(2026, 1, 1),
    )
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="1", is_interest_bearing=True)
    asset = Asset.objects.create(ticker="NVDA", description="Nvidia", asset_type="FOREIGN_EQUITY")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(event_type="BUY", account=conta, asset=asset,
                                   trade_date=date(2026, 1, 5), quantity=Decimal(10),
                                   price_usd=Decimal(100), fee_usd=Decimal(0)))
    return conta, asset


def _registrar(conta, **kw):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(dict(account=conta, **kw))


def _posicao(conta, asset):
    return PositionService().position(conta, asset)


# ------------------------------------------------------------- split 2:1

def test_split_duplica_quantidade_e_preserva_custo(setup):
    conta, asset = setup
    _registrar(conta, event_type="STOCK_SPLIT", asset=asset, trade_date=date(2026, 2, 1),
               split_ratio_from=Decimal(1), split_ratio_to=Decimal(2))
    pos = _posicao(conta, asset)
    assert pos["quantity"] == Decimal(20)
    # custo total BRL inalterado: 10×100×5 = R$ 5.000
    assert pos["cost_brl_total"] == Decimal(5000)
    assert pos["avg_cost_usd"] == Decimal(50)  # 1000/20


def test_venda_pos_split_baixa_custo_corretamente(setup):
    conta, asset = setup
    _registrar(conta, event_type="STOCK_SPLIT", asset=asset, trade_date=date(2026, 2, 1),
               split_ratio_from=Decimal(1), split_ratio_to=Decimal(2))
    ev = _registrar(conta, event_type="SELL", asset=asset, trade_date=date(2026, 3, 1),
                    quantity=Decimal(15), price_usd=Decimal(60), fee_usd=Decimal(0))
    realizado = PositionService().realized(conta, asset)
    r = next(r for r in realizado if r["event"].pk == ev.pk)
    assert r["cost_sold_brl"] == Decimal("3750.00")  # 15 × 250 BRL
    assert r["gain_brl"] == Decimal("750.00")        # 15×60×5 − 3750
    pos = _posicao(conta, asset)
    assert pos["quantity"] == Decimal(5)
    assert pos["cost_brl_total"] == Decimal(1250)    # 5000 − 3750


def test_reverse_split_reduz_quantidade_e_preserva_custo(setup):
    conta, asset = setup
    _registrar(conta, event_type="REVERSE_SPLIT", asset=asset, trade_date=date(2026, 2, 1),
               split_ratio_from=Decimal(2), split_ratio_to=Decimal(1))
    pos = _posicao(conta, asset)
    assert pos["quantity"] == Decimal(5)
    assert pos["cost_brl_total"] == Decimal(5000)
    assert pos["avg_cost_usd"] == Decimal(200)


# ---------------------------------------------------------- cash-in-lieu

def test_cash_in_lieu_baixa_custo_e_apura_alienacao(setup):
    """CT-017: reverse 1:10 sobre 10 ações → 1 ação + fração 0,5? Neste
    cenário: reverse 10:1 não gera fração; usa-se 11 ações → 1,1 → 1 ação +
    0,1 paga em dinheiro. Simplificado: 15→1:10 dá 1,5 → 1 ação + 0,5 em
    dinheiro (cash-in-lieu com quantidade 0,5 e valor US$ 25)."""
    conta, asset = setup
    # acrescenta 5 ações (total 15) @100
    _registrar(conta, event_type="BUY", asset=asset, trade_date=date(2026, 1, 20),
               quantity=Decimal(5), price_usd=Decimal(100), fee_usd=Decimal(0))
    # reverse 10:1: 15 → 1,5; corretora liquida 0,5 em dinheiro
    _registrar(conta, event_type="REVERSE_SPLIT", asset=asset, trade_date=date(2026, 2, 1),
               split_ratio_from=Decimal(10), split_ratio_to=Decimal(1))
    pos = _posicao(conta, asset)
    assert pos["quantity"] == Decimal("1.5")
    ev = _registrar(conta, event_type="CASH_IN_LIEU", asset=asset,
                    trade_date=date(2026, 2, 2), quantity=Decimal("0.5"),
                    amount_usd=Decimal(25))
    realizado = PositionService().realized(conta, asset)
    r = next(r for r in realizado if r["event"].pk == ev.pk)
    # custo baixado: 0,5 × custo médio 7500/1,5 = 2500 BRL
    assert r["cost_sold_brl"] == Decimal("2500.00")
    # alienação: US$ 25 × 5 = 125 BRL → prejuízo proporcional
    assert r["sale_brl"] == Decimal("125.00")
    assert r["gain_brl"] == Decimal("-2375.00")
    assert _posicao(conta, asset)["quantity"] == Decimal(1)


def test_cash_in_lieu_conta_como_rendimento_no_engine(setup):
    conta, asset = setup
    _registrar(conta, event_type="BUY", asset=asset, trade_date=date(2026, 1, 20),
               quantity=Decimal(5), price_usd=Decimal(100), fee_usd=Decimal(0))
    _registrar(conta, event_type="REVERSE_SPLIT", asset=asset, trade_date=date(2026, 2, 1),
               split_ratio_from=Decimal(10), split_ratio_to=Decimal(1))
    _registrar(conta, event_type="CASH_IN_LIEU", asset=asset,
               trade_date=date(2026, 2, 2), quantity=Decimal("0.5"),
               amount_usd=Decimal(600))
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        resultado = TaxEngine(2026).compute()
    # alienação 3000 − custo baixado 2500 = ganho 500 entra na apuração
    assert resultado["income_brl"] == Decimal("500.00")


def test_split_nao_exige_preco_nem_valor(setup):
    conta, asset = setup
    ev = _registrar(conta, event_type="STOCK_SPLIT", asset=asset,
                    trade_date=date(2026, 2, 1),
                    split_ratio_from=Decimal(1), split_ratio_to=Decimal(4))
    assert ev.amount_usd == Decimal(0)
    assert ev.price_usd is None


def test_split_exige_razao(setup):
    conta, asset = setup
    with pytest.raises(ValueError, match="razão"):
        _registrar(conta, event_type="STOCK_SPLIT", asset=asset,
                   trade_date=date(2026, 2, 1))


def test_form_exibe_campos_de_split():
    from ledger.forms import EventForm
    form = EventForm()
    assert "split_ratio_from" in form.fields
    assert "split_ratio_to" in form.fields


def test_cash_in_lieu_exige_posicao_suficiente(setup):
    conta, asset = setup
    with pytest.raises(ValueError, match="posição insuficiente"):
        _registrar(conta, event_type="CASH_IN_LIEU", asset=asset,
                   trade_date=date(2026, 2, 2), quantity=Decimal(99),
                   amount_usd=Decimal(1))
