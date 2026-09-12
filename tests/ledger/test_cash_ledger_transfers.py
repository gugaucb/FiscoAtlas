"""E2E browser (ticket 01 e2e-browser-regressao) revelou: CashLedgerService
somava amount_usd de TODA linha — a custódia de ativos (que não movimenta
caixa) inflava o caixa nas duas contas, e a ponta OUT da transferência de
caixa somava positivo em vez de subtrair. Regressão: caixa não muda com
transferência de ativos; mudança só na transferência de caixa.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from ledger.cash import CashLedgerService
from ledger.models import Asset, BrokerAccount
from ledger.service import BrokerTransferService, EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def contas(residente):
    a = BrokerAccount.objects.create(broker_name="Schwab", account_number="A")
    b = BrokerAccount.objects.create(broker_name="IBKR", account_number="B")
    return a, b


def _aporte(conta, usd, dia=date(2026, 1, 5)):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="APORTE", account=conta, trade_date=dia,
            amount_usd=usd,
        ))


def test_custodia_de_ativo_nao_movimenta_caixa(residente, contas):
    """Transferir ações entre contas NÃO altera caixa de nenhuma das pontas."""
    a, b = contas
    aapl = Asset.objects.create(ticker="AAPL", description="Apple",
                                asset_type="FOREIGN_EQUITY")
    _aporte(a, Decimal(10000))
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="BUY", account=a, asset=aapl, trade_date=date(2026, 1, 10),
            quantity=Decimal(100), price_usd=Decimal(50), fee_usd=Decimal(0),
        ))  # caixa A: 10000 − 5000 = 5000
    with mock.patch.object(BrokerTransferService, "_ptax_rate", return_value=RATE):
        BrokerTransferService().record(
            out_account=a, in_account=b, asset=aapl,
            trade_date=date(2026, 2, 1), quantity=Decimal(40),
        )
    # o custo da custódia (US$2.000) não pode entrar no caixa de nenhuma conta
    assert CashLedgerService().balance(a) == Decimal("5000.00")
    assert CashLedgerService().balance(b) == Decimal("0.00")


def test_transferencia_de_caixa_move_saldo(residente, contas):
    """Ponta OUT subtrai, ponta IN soma (não: ambas somando positivo)."""
    a, b = contas
    _aporte(a, Decimal(10000))
    _aporte(b, Decimal(1000))
    with mock.patch.object(BrokerTransferService, "_ptax_rate", return_value=RATE):
        BrokerTransferService().record(
            out_account=a, in_account=b,
            trade_date=date(2026, 3, 1), amount_usd=Decimal(4000),
        )
    assert CashLedgerService().balance(a) == Decimal("6000.00")
    assert CashLedgerService().balance(b) == Decimal("5000.00")