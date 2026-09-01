from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from ledger.models import Asset, FinancialEvent
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def account(db):
    from ledger.models import BrokerAccount
    return BrokerAccount.objects.create(broker_name="Avenue", account_number="123")


def test_aporte_sem_asset(client, account):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        resp = client.post("/eventos/novo/", {
            "event_type": "APORTE", "account": account.pk,
            "trade_date": "2026-01-05", "amount_usd": "5000",
        })
    assert resp.status_code == 302
    ev = FinancialEvent.objects.get(event_type="APORTE")
    assert ev.asset is None
    assert ev.amount_usd == Decimal("5000")


def test_buy_com_ticker_novo_cria_asset(client, account):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        resp = client.post("/eventos/novo/", {
            "event_type": "BUY", "account": account.pk, "asset_ticker": "tsla",
            "trade_date": "2026-02-01", "quantity": "10", "price_usd": "200",
        })
    assert resp.status_code == 302
    asset = Asset.objects.get(ticker="TSLA")
    ev = FinancialEvent.objects.get(event_type="BUY")
    assert ev.asset == asset


def test_labels_em_ptbr(client, account):
    html = client.get("/eventos/novo/").content.decode()
    assert "Tipo de evento" in html
    assert "Ativo (ticker)" in html
    assert "Data da operação" in html
    assert "Quantidade" in html
    assert "Preço (USD)" in html
    assert "Valor (USD)" in html


def test_buy_sem_quantidade_rejeitado(client, account):
    resp = client.post("/eventos/novo/", {
        "event_type": "BUY", "account": account.pk, "asset_ticker": "AAPL",
        "trade_date": "2026-02-01",
    })
    assert resp.status_code == 200
    assert "obrigatório" in resp.content.decode().lower()


def test_dividendo_com_valor_por_acao(client, account):
    from ledger.models import Asset
    Asset.objects.create(ticker="AAPL", description="Apple", asset_type="STOCK")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        resp = client.post("/eventos/novo/", {
            "event_type": "DIVIDEND", "account": account.pk, "asset_ticker": "AAPL",
            "trade_date": "2026-03-01", "quantity": "25", "per_share_usd": "1",
            "tax_usd": "3.75",
        })
    assert resp.status_code == 302
    ev = FinancialEvent.objects.get(event_type="DIVIDEND")
    assert ev.amount_usd == Decimal("21.25")  # 25*1 - 3.75
