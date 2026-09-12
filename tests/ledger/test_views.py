from decimal import Decimal
from unittest import mock
import pytest
from ledger.models import Asset, BrokerAccount

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(db):
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    return acct, asset


def test_event_list_empty(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_new_event_form_creates_buy(client, setup):
    acct, asset = setup
    with mock.patch("ledger.views.EventService._ptax_rate", return_value=Decimal("5")):
        resp = client.post("/eventos/novo/", {
            "event_type": "BUY", "account": acct.pk, "asset_ticker": "AAPL",
            "trade_date": "2026-03-10", "quantity": "10", "price_usd": "100",
            "fee_usd": "1", "notes": "",
        })
    assert resp.status_code == 302
    assert b"AAPL" in client.get("/").content


def test_form_rejects_invalid_sell(client, setup):
    acct, asset = setup
    with mock.patch("ledger.views.EventService._ptax_rate", return_value=Decimal("5")):
        resp = client.post("/eventos/novo/", {
            "event_type": "SELL", "account": acct.pk, "asset_ticker": "AAPL",
            "trade_date": "2026-03-11", "quantity": "5", "price_usd": "110", "fee_usd": "1",
        })
    assert resp.status_code == 200  # re-render com erro
    assert b"insuficiente" in resp.content


def test_positions_page(client, setup):
    acct, asset = setup
    with mock.patch("ledger.views.EventService._ptax_rate", return_value=Decimal("5")):
        client.post("/eventos/novo/", {
            "event_type": "BUY", "account": acct.pk, "asset_ticker": "AAPL",
            "trade_date": "2026-03-10", "quantity": "10", "price_usd": "100", "fee_usd": "1",
        })
    html = client.get("/posicoes/").content.decode()
    assert "AAPL" in html and "10" in html


def test_positions_page_inclui_posicao_so_de_abertura(client, setup):
    """Achado P1 do auditor (19): carteira carregada exclusivamente por
    OpeningPosition (nenhum evento) é custódia real — aparece no relatório,
    no CBE e na reconciliação, mas a tela /posicoes/ descobria contas e
    ativos só por FinancialEvent e a omitia."""
    acct, asset = setup
    from ledger.models import OpeningPosition
    OpeningPosition.objects.create(
        account=acct, asset=asset, quantity=Decimal(100), total_cost_brl=Decimal("20000"),
    )
    html = client.get("/posicoes/").content.decode()
    assert "AAPL" in html and "100" in html  # falha no código atual


def test_cash_page_shows_balance(client, setup):
    acct, asset = setup
    with mock.patch("ledger.views.EventService._ptax_rate", return_value=Decimal("5")):
        client.post("/eventos/novo/", {
            "event_type": "APORTE", "account": acct.pk,
            "trade_date": "2026-03-01", "amount_usd": "5000",
        })
    html = client.get("/caixa/").content.decode()
    assert "5000" in html


def test_correct_event_page(client, setup):
    acct, asset = setup
    with mock.patch("ledger.views.EventService._ptax_rate", return_value=Decimal("5")):
        client.post("/eventos/novo/", {
            "event_type": "APORTE", "account": acct.pk,
            "trade_date": "2026-03-01", "amount_usd": "5000",
        })
        ev_id = acct.events.first().pk
        resp = client.post(f"/eventos/{ev_id}/corrigir/", {
            "event_type": "APORTE", "account": acct.pk,
            "trade_date": "2026-03-01", "amount_usd": "4000",
        })
    assert resp.status_code == 302
    assert acct.events.count() == 2
