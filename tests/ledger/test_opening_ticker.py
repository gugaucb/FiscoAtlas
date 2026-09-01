import pytest
from ledger.models import Asset, OpeningPosition

pytestmark = pytest.mark.django_db


def test_abertura_com_ticker_novo_cria_asset(client):
    resp = client.post("/posicao-abertura/", {
        "asset_ticker": "msft", "reference_date": "2025-12-31",
        "quantity": "10", "total_cost_brl": "5000",
    })
    assert resp.status_code == 302
    asset = Asset.objects.get(ticker="MSFT")
    assert asset.asset_type == "STOCK"
    op = OpeningPosition.objects.get(asset=asset)
    assert op.quantity == 10
    assert op.total_cost_brl == 5000


def test_abertura_rotulo_ticker(client):
    html = client.get("/posicao-abertura/").content.decode()
    assert "Ativo (ticker)" in html
