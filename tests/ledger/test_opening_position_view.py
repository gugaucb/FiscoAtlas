from decimal import Decimal
import pytest
from ledger.models import Asset, BrokerAccount, OpeningPosition

pytestmark = pytest.mark.django_db


def test_opening_position_create(client, db):
    Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    resp = client.post("/posicao-abertura/", {
        "asset_ticker": "AAPL", "reference_date": "2025-12-31",
        "quantity": "100", "total_cost_brl": "95000", "notes": "",
    })
    assert resp.status_code == 302
    op = OpeningPosition.objects.first()
    assert op.quantity == Decimal(100)
    assert op.average_cost_brl == Decimal(950)
    assert b"AAPL" in client.get("/posicao-abertura/").content
