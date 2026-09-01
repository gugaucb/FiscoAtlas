"""FEE e TAX_WITHHELD são saídas de caixa: o sistema converte para negativo."""
from decimal import Decimal

import pytest
from django.utils import timezone

from ledger.models import BrokerAccount, FinancialEvent
from ledger.service import EventService

pytestmark = pytest.mark.django_db


@pytest.fixture
def conta():
    return BrokerAccount.objects.create(broker_name="Avenue", account_number="1")


@pytest.fixture(autouse=True)
def _sem_bcb(monkeypatch):
    from fx.service import PtaxService

    def boom(self, day):
        raise AssertionError("BCB não deve ser chamado: teste usa PTAX manual")

    monkeypatch.setattr(PtaxService, "_fetch_bcb", boom)


def _record(etype, amount):
    return EventService().record({
        "event_type": etype,
        "account": BrokerAccount.objects.get(),
        "trade_date": timezone.now().date(),
        "amount_usd": Decimal(amount),
        "ptax_manual": Decimal("5.00"),
        "ptax_reason": "teste",
    })


def test_fee_positivo_vira_saida(conta):
    ev = _record("FEE", "5")
    assert ev.amount_usd == Decimal("-5.00")


def test_tax_withheld_positivo_vira_saida(conta):
    ev = _record("TAX_WITHHELD", "10")
    assert ev.amount_usd == Decimal("-10.00")


def test_fee_ja_negativo_nao_duplica_sinal(conta):
    ev = _record("FEE", "-7")
    assert ev.amount_usd == Decimal("-7.00")


def test_withdrawal_positivo_vira_saida(conta):
    ev = _record("WITHDRAWAL", "1000")
    assert ev.amount_usd == Decimal("-1000.00")
