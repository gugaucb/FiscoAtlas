"""Ticket 06 (roadmap-compliance) — Transferências de custódia entre corretoras.

RF-IMP-008, RF-CST-003/004, CT-014/CT-015: transferência entre contas do
mesmo titular NÃO é alienação — transporta quantidade e custo histórico BRL
integralmente. Par pareado via transfer_pair_id; ponta solta → alerta.
"""
from datetime import date
from decimal import Decimal
from unittest import mock
from uuid import uuid4

import pytest

from fiscal.engine import TaxEngine
from fiscal.models import TaxRule
from ledger.models import Asset, BrokerAccount, FinancialEvent
from ledger.position import PositionService
from ledger.service import BrokerTransferService, EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def contas(residente, db):
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, quote_type="VENDA", date_rule="INCOME_RECEIPT_DATE",
        effective_from=date(2026, 1, 1),
    )
    a = BrokerAccount.objects.create(broker_name="Schwab", account_number="A")
    b = BrokerAccount.objects.create(broker_name="IBKR", account_number="B")
    return a, b


@pytest.fixture
def aapl(db):
    return Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")


def _compra(conta, asset, qty=Decimal(100), price=Decimal(150), dia=date(2026, 1, 5)):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(dict(
            event_type="BUY", account=conta, asset=asset, trade_date=dia,
            quantity=qty, price_usd=price, fee_usd=Decimal(0),
        ))


# ------------------------------------------------------------- CT-014

def test_ct014_transferencia_transporta_quantidade_e_custo(contas, aapl):
    a, b = contas
    _compra(a, aapl)  # 100 @150 = US$15.000 = R$75.000
    with mock.patch.object(BrokerTransferService, "_ptax_rate", return_value=RATE):
        BrokerTransferService().record(
            out_account=a, in_account=b, asset=aapl,
            trade_date=date(2026, 2, 1), quantity=Decimal(40),
        )
    pa = PositionService().position(a, aapl)
    pb = PositionService().position(b, aapl)
    assert pa["quantity"] == Decimal(60)
    assert pa["cost_brl_total"] == Decimal(45000)
    assert pb["quantity"] == Decimal(40)
    assert pb["cost_brl_total"] == Decimal(30000)


def test_ct014_transferencia_nao_apura_ganho(contas, aapl):
    a, b = contas
    _compra(a, aapl)
    with mock.patch.object(BrokerTransferService, "_ptax_rate", return_value=RATE):
        BrokerTransferService().record(
            out_account=a, in_account=b, asset=aapl,
            trade_date=date(2026, 2, 1), quantity=Decimal(40),
        )
    assert PositionService().realized(a, aapl) == []
    assert PositionService().realized(b, aapl) == []
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        resultado = TaxEngine(2026).compute()
    assert resultado["income_brl"] == Decimal("0.00")
    assert resultado["taxable_brl"] == Decimal("0.00")


def test_par_pareado_mesmo_transfer_pair_id(contas, aapl):
    a, b = contas
    _compra(a, aapl)
    with mock.patch.object(BrokerTransferService, "_ptax_rate", return_value=RATE):
        BrokerTransferService().record(
            out_account=a, in_account=b, asset=aapl,
            trade_date=date(2026, 2, 1), quantity=Decimal(40),
        )
    pares = FinancialEvent.objects.filter(
        event_type__in=("BROKER_TRANSFER_IN", "BROKER_TRANSFER_OUT"),
    )
    assert pares.count() == 2
    assert len({p.transfer_pair_id for p in pares}) == 1


def test_transferencia_exige_posicao_suficiente(contas, aapl):
    a, b = contas
    _compra(a, aapl, qty=Decimal(10))
    with mock.patch.object(BrokerTransferService, "_ptax_rate", return_value=RATE):
        with pytest.raises(ValueError, match="posição insuficiente"):
            BrokerTransferService().record(
                out_account=a, in_account=b, asset=aapl,
                trade_date=date(2026, 2, 1), quantity=Decimal(40),
            )


# ------------------------------------------------- venda pós-transferência

def test_venda_apos_transferencia_baixa_custo_corretamente(contas, aapl):
    a, b = contas
    _compra(a, aapl)
    with mock.patch.object(BrokerTransferService, "_ptax_rate", return_value=RATE):
        BrokerTransferService().record(
            out_account=a, in_account=b, asset=aapl,
            trade_date=date(2026, 2, 1), quantity=Decimal(40),
        )
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        ev = EventService().record(dict(
            event_type="SELL", account=b, asset=aapl, trade_date=date(2026, 3, 1),
            quantity=Decimal(40), price_usd=Decimal(160), fee_usd=Decimal(0),
        ))
    r = PositionService().realized(b, aapl)[0]
    assert r["cost_sold_brl"] == Decimal(30000)
    assert r["gain_brl"] == Decimal(40 * 160 * 5 - 30000)  # 2000


# ------------------------------------------------- CT-015 ponta solta

def test_ponta_solta_gera_alerta_no_validator(contas, aapl):
    a, b = contas
    _compra(a, aapl)
    # OUT sem ponta pareada (registro direto, fora do serviço)
    FinancialEvent.objects.create(
        event_type="BROKER_TRANSFER_OUT", account=a, asset=aapl,
        trade_date=date(2026, 2, 1), quantity=Decimal(40),
        amount_usd=Decimal(6000), fx_rate=RATE, amount_brl=Decimal(30000),
        fee_usd=Decimal(0), tax_usd=Decimal(0), transfer_pair_id=uuid4(),
    )
    from fiscal.validator import AnnualClosingValidator
    with pytest.raises(Exception, match="inconsis"):
        AnnualClosingValidator(2026).validate_or_raise()


def test_par_completo_nao_gera_alerta(contas, aapl):
    a, b = contas
    _compra(a, aapl)
    with mock.patch.object(BrokerTransferService, "_ptax_rate", return_value=RATE):
        BrokerTransferService().record(
            out_account=a, in_account=b, asset=aapl,
            trade_date=date(2026, 2, 1), quantity=Decimal(40),
        )
    from fiscal.validator import AnnualClosingValidator
    AnnualClosingValidator(2026).validate_or_raise()  # não levanta
