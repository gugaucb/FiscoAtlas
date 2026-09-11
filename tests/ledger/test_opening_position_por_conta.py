"""Auditoria-fiscal 03 — abertura e posição estritamente por conta.

Antes: _opening() ignorava a conta (filter(asset=asset).first()), então com
duas corretoras segurando o mesmo ativo as aberturas se misturavam entre
contas (a primeira encontrada valia para todas). Testes antigos só usavam
uma conta e não detectavam o defeito.
"""
from decimal import Decimal

import pytest

from ledger.models import Asset, BrokerAccount, OpeningPosition
from ledger.position import PositionService

pytestmark = pytest.mark.django_db


@pytest.fixture
def duas_contas(db):
    av = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    sc = BrokerAccount.objects.create(broker_name="Schwab", account_number="2")
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    OpeningPosition.objects.create(
        account=av, asset=aapl, reference_date="2025-12-31",
        quantity=Decimal(100), total_cost_brl=Decimal("50000"),
    )
    OpeningPosition.objects.create(
        account=sc, asset=aapl, reference_date="2025-12-31",
        quantity=Decimal(50), total_cost_brl=Decimal("40000"),
    )
    return av, sc, aapl


def test_abertura_independente_por_conta(duas_contas):
    """Avenue: 100 AAPL / R$ 50.000. Schwab: 50 AAPL / R$ 40.000.
    Jamais 150, nem 100+100, nem 50+50."""
    av, sc, aapl = duas_contas
    pos_av = PositionService().position(av, aapl)
    pos_sc = PositionService().position(sc, aapl)
    assert pos_av["quantity"] == Decimal(100)
    assert pos_av["cost_brl_total"] == Decimal("50000")
    assert pos_sc["quantity"] == Decimal(50)
    assert pos_sc["cost_brl_total"] == Decimal("40000")


def test_eventos_nao_vazam_entre_contas(duas_contas):
    """Compra na Avenue não altera a posição/custo da Schwab."""
    from ledger.models import FinancialEvent
    av, sc, aapl = duas_contas
    FinancialEvent.objects.create(
        account=av, asset=aapl, event_type="BUY", trade_date="2026-02-01",
        quantity=Decimal(10), price_usd=Decimal(200), amount_usd=Decimal(-2000),
        amount_brl=Decimal(-11000), fx_rate=Decimal("5.5"),
    )
    pos_av = PositionService().position(av, aapl)
    pos_sc = PositionService().position(sc, aapl)
    assert pos_av["quantity"] == Decimal(110)
    assert pos_sc["quantity"] == Decimal(50)
    assert pos_sc["cost_brl_total"] == Decimal("40000")


def test_abertura_sem_conta_com_duas_contas_bloqueia(duas_contas):
    """Abertura legada sem conta com 2+ contas ativas: ambígua — bloqueia,
    não adivinha (auditoria-fiscal 03)."""
    av, sc, aapl = duas_contas
    OpeningPosition.objects.create(
        account=None, asset=aapl, reference_date="2025-12-31",
        quantity=Decimal(7), total_cost_brl=Decimal("7000"),
    )
    terceira = BrokerAccount.objects.create(broker_name="Clear", account_number="3")
    with pytest.raises(ValueError, match="reconcilie"):
        PositionService().position(terceira, aapl)


def test_abertura_sem_conta_com_conta_unica_herdeira(duas_contas):
    """Abertura legada sem conta é herdada somente quando inequívoca
    (1 conta ativa)."""
    av, sc, aapl = duas_contas
    BrokerAccount.objects.filter(pk__in=[av.pk, sc.pk]).update(active=False)
    solitaria = BrokerAccount.objects.create(broker_name="Unica", account_number="9")
    OpeningPosition.objects.create(
        account=None, asset=aapl, reference_date="2025-12-31",
        quantity=Decimal(7), total_cost_brl=Decimal("7000"),
    )
    pos = PositionService().position(solitaria, aapl)
    assert pos["quantity"] == Decimal(7)
    assert pos["cost_brl_total"] == Decimal("7000")
