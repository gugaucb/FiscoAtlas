"""Desativar evento (soft delete): sai de tudo, registro permanece."""
from datetime import date
from decimal import Decimal

import pytest

from ledger.models import Asset, BrokerAccount, FinancialEvent
from ledger.position import PositionService

pytestmark = pytest.mark.django_db


@pytest.fixture
def conta_com_buy():
    conta = BrokerAccount.objects.create(
        broker_name="Avenue", account_number="SD", country_code="US",
        is_interest_bearing=True, name="Avenue SD",
    )
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY", country_code="US")
    from fx.models import PtaxRate
    from fx.service import PtaxService
    PtaxService().override(date(2026, 1, 10), Decimal("5.4"), "teste")
    ev = FinancialEvent.objects.create(
        account=conta, asset=asset, event_type="BUY", trade_date=date(2026, 1, 10),
        quantity=Decimal("10"), price_usd=Decimal("100"), fee_usd=Decimal(0), tax_usd=Decimal(0),
        amount_usd=Decimal("-1000"), fx_rate=Decimal("5.4"), amount_brl=Decimal("-5400"),
    )
    return conta, asset, ev


def test_post_desativa_sem_deletar(client, conta_com_buy):
    conta, asset, ev = conta_com_buy
    resp = client.post(f"/eventos/{ev.pk}/desativar/")
    assert resp.status_code == 302
    ev.refresh_from_db()
    assert ev.active is False  # soft delete: registro permanece
    assert FinancialEvent.objects.filter(pk=ev.pk).exists()


def test_desativado_nao_contabiliza_em_posicao(client, conta_com_buy):
    conta, asset, ev = conta_com_buy
    pos_antes = PositionService().position(conta, asset)
    assert pos_antes["quantity"] == 10
    client.post(f"/eventos/{ev.pk}/desativar/")
    pos_depois = PositionService().position(conta, asset)
    assert pos_depois["quantity"] == 0


def test_desativado_sai_da_listagem(client, conta_com_buy):
    conta, asset, ev = conta_com_buy
    assert ev.pk in client.get("/").context["events"].values_list("pk", flat=True)
    client.post(f"/eventos/{ev.pk}/desativar/")
    assert ev.pk not in client.get("/").context["events"].values_list("pk", flat=True)


def test_get_nao_desativa(client, conta_com_buy):
    conta, asset, ev = conta_com_buy
    client.get(f"/eventos/{ev.pk}/desativar/")
    ev.refresh_from_db()
    assert ev.active is True
