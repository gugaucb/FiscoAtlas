import pytest
from ledger.models import Asset, BrokerAccount, OpeningPosition

pytestmark = pytest.mark.django_db


def test_abertura_com_ticker_novo_exige_cadastro_previo(client):
    """SUBSTITUÍDO (P0 do auditor): o teste antigo exigia que ticker novo
    criasse asset com asset_type='STOCK' — valor FORA da taxonomia legal
    (RF-AST-003/006: fim da auto-criação silenciosa de ativos) e criação
    silenciosa de ativo sem classificação jurídica. O comportamento correto
    é recusar o lançamento e orientar o cadastro em /ativos/novo/."""
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    resp = client.post("/posicao-abertura/", {
        "account": conta.pk, "asset_ticker": "msft", "reference_date": "2025-12-31",
        "quantity": "10", "total_cost_brl": "5000",
    })
    assert resp.status_code == 200  # re-renderiza com erro
    assert not Asset.objects.filter(ticker="MSFT").exists()
    assert not OpeningPosition.objects.exists()
    assert b"ativos/novo/" in resp.content


def test_abertura_rotulo_ticker(client):
    html = client.get("/posicao-abertura/").content.decode()
    assert "Ativo (ticker)" in html
