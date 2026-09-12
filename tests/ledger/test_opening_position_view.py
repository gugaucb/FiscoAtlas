from decimal import Decimal
import pytest
from ledger.models import Asset, BrokerAccount, OpeningPosition

pytestmark = pytest.mark.django_db


def test_opening_position_create(client, db):
    # Auditoria-fiscal 03: abertura é por conta — campo obrigatório
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    resp = client.post("/posicao-abertura/", {
        "account": conta.pk, "asset_ticker": "AAPL", "reference_date": "2025-12-31",
        "quantity": "100", "total_cost_brl": "95000", "notes": "",
    })
    assert resp.status_code == 302
    op = OpeningPosition.objects.first()
    assert op.quantity == Decimal(100)
    assert op.average_cost_brl == Decimal(950)
    assert b"AAPL" in client.get("/posicao-abertura/").content


def test_opening_position_nao_cria_ativo_automatico(client, db):
    """P0 do auditor: o formulário usava get_or_create com asset_type='STOCK'
    (fora da taxonomia legal) — ticker inexistente criava ativo não
    classificado silenciosamente. Agora exige cadastro prévio."""
    from django.core.exceptions import ValidationError
    from ledger.opening_forms import OpeningPositionForm
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    form = OpeningPositionForm(data={
        "account": conta.pk, "asset_ticker": "MSFT", "reference_date": "2025-12-31",
        "quantity": "10", "total_cost_brl": "1000",
    })
    assert not form.is_valid()
    assert "ativos/novo/" in str(form.errors)
    assert not Asset.objects.filter(ticker="MSFT").exists()
    # ativo inativo também é rejeitado
    Asset.objects.create(ticker="MSFT", description="MS", asset_type="FOREIGN_EQUITY", active=False)
    form = OpeningPositionForm(data={
        "account": conta.pk, "asset_ticker": "MSFT", "reference_date": "2025-12-31",
        "quantity": "10", "total_cost_brl": "1000",
    })
    assert not form.is_valid()
    assert not OpeningPosition.objects.exists()
