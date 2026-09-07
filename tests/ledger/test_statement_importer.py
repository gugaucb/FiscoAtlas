"""Ticket 12 (roadmap-compliance) — Ingestão de extratos CSV (RF-IMP-001..004).

CT-030: reimportar o mesmo arquivo não duplica eventos (dedup por hash do
arquivo). ImportBatch registra hash, data e contagem.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from ledger.importers.schwab import SchwabStatementImporter
from ledger.models import Asset, BrokerAccount, FinancialEvent, ImportBatch
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db

CSV_EXEMPLO = """Date,Action,Symbol,Description,Quantity,Price,Amount,Fees
01/05/2026,Buy,AAPL,Apple Inc.,10,100.00,-1000.00,0.00
03/15/2026,Dividend,AAPL,Dividend,10,1.00,9.00,0.00
"""


@pytest.fixture
def ambiente(residente, db):
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    return conta


def test_importa_csv_schwab(ambiente):
    conta = ambiente
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        batch = SchwabStatementImporter(conta).import_csv(CSV_EXEMPLO)
    eventos = FinancialEvent.objects.order_by("trade_date")
    assert eventos.count() == 2
    compra, dividendo = eventos
    assert compra.event_type == "BUY"
    assert compra.quantity == Decimal(10)
    assert dividendo.event_type == "DIVIDEND"
    assert dividendo.amount_usd == Decimal("9.00")
    assert batch.events_created == 2
    assert batch.file_hash


def test_ct030_reimport_nao_duplica(ambiente):
    conta = ambiente
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        SchwabStatementImporter(conta).import_csv(CSV_EXEMPLO)
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        batch2 = SchwabStatementImporter(conta).import_csv(CSV_EXEMPLO)
    assert FinancialEvent.objects.count() == 2
    assert batch2.events_created == 0


def test_import_batch_registra_hash_e_data(ambiente):
    conta = ambiente
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        batch = SchwabStatementImporter(conta).import_csv(CSV_EXEMPLO)
    assert ImportBatch.objects.filter(file_hash=batch.file_hash).exists()
    assert batch.imported_at is not None


def _post_csv(client, conta_id):
    from io import BytesIO
    return client.post(f"/contas/{conta_id}/importar/", {
        "arquivo": BytesIO(CSV_EXEMPLO.encode("utf-8")),
    })


def test_view_upload_importa(client, ambiente):
    from django.contrib.auth.models import User
    User.objects.create_user("g", password="x")
    client.force_login(User.objects.get(username="g"))
    resp = _post_csv(client, ambiente.pk)
    assert resp.status_code == 302
    assert FinancialEvent.objects.count() == 2


def test_view_preview(client, ambiente):
    from django.contrib.auth.models import User
    User.objects.create_user("g", password="x")
    client.force_login(User.objects.get(username="g"))
    resp = client.get(f"/contas/{ambiente.pk}/importar/", data={"csv": CSV_EXEMPLO})
    assert resp.status_code == 200
    assert b"Buy" in resp.content
