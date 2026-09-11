"""Ticket 12 (roadmap-compliance) — Ingestão de extratos CSV (RF-IMP-001..004).

CT-030: reimportar o mesmo arquivo não duplica eventos (dedup por hash do
arquivo). ImportBatch registra hash, data e contagem.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from ledger.importers.base import StatementImportError
from ledger.importers.schwab import SchwabStatementImporter
from ledger.models import Asset, BrokerAccount, FinancialEvent, ImportBatch, ImportIssue
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db

CSV_EXEMPLO = """Date,Action,Symbol,Description,Quantity,Price,Amount,Fees
01/05/2026,Buy,AAPL,Apple Inc.,10,100.00,-1000.00,0.00
03/15/2026,Dividend,AAPL,Dividend,10,1.00,9.00,0.00
"""

CSV_SELL = """Date,Action,Symbol,Description,Quantity,Price,Amount,Fees
01/05/2026,Buy,AAPL,Apple Inc.,10,100.00,-1000.00,0.00
04/10/2026,Sell,AAPL,Sale,4,120.00,480.00,1.00
"""

CSV_MISTO = """Date,Action,Symbol,Description,Quantity,Price,Amount,Fees
01/05/2026,Buy,AAPL,Apple Inc.,10,100.00,-1000.00,0.00
04/20/2026,Transfer,AAPL,Journal,10,0.00,0.00,0.00
04/22/2026,Fee Received,AAPL,Unknown action,0,0.00,5.00,0.00
"""


# ---- Auditoria-fiscal 01: nenhuma linha desaparece silenciosamente ----

def test_sell_importado_como_evento_venda(ambiente):
    """Regressão (auditoria-fiscal 01): antes, Sell era descartada na leitura
    (ACTION_MAP sem 'sell' + continue silencioso) — fato tributável inteiro
    desaparecia. Agora vira evento SELL."""
    conta = ambiente
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        batch = SchwabStatementImporter(conta).import_csv(CSV_SELL)
    eventos = FinancialEvent.objects.order_by("trade_date")
    assert eventos.count() == 2
    compra, venda = eventos
    assert compra.event_type == "BUY"
    assert venda.event_type == "SELL"
    assert venda.quantity == Decimal(4)
    assert venda.amount_usd == Decimal("479.00")  # 4*120 - 1 de taxa
    assert batch.rows_source == 2
    assert batch.rows_imported == 2
    assert batch.rows_unsupported == 0
    assert batch.reconciled


def test_preview_mostra_linha_nao_suportada(ambiente):
    """Regressão (auditoria-fiscal 01): antes, ação desconhecida simplesmente
    não aparecia na prévia. Agora vira pendência visível e bloqueante."""
    conta = ambiente
    preview = SchwabStatementImporter(conta).preview(CSV_MISTO)
    assert len(preview) == 3  # nada desaparece
    pendente = [r for r in preview if r["status"] == "UNSUPPORTED"]
    assert len(pendente) == 2
    transfer = next(r for r in pendente if r["raw_action"] == "Transfer")
    assert transfer["severity"] == "BLOCKING"
    assert transfer["line"] == 3
    assert transfer["reason"]


def test_import_sem_reconhecimento_bloqueia(ambiente):
    """Importação com pendências exige reconhecimento explícito do usuário."""
    conta = ambiente
    with pytest.raises(StatementImportError) as e:
        SchwabStatementImporter(conta).import_csv(CSV_MISTO)
    assert "não suportada" in str(e.value)
    assert not ImportBatch.objects.exists()  # transação rollback
    assert FinancialEvent.objects.count() == 0


def test_import_com_reconhecimento_cria_issues(ambiente):
    """Com reconhecimento explícito, importadas + pendências conciliam com
    o arquivo e cada linha não suportada vira ImportIssue PENDING."""
    conta = ambiente
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        batch = SchwabStatementImporter(conta).import_csv(
            CSV_MISTO, acknowledge_pending=True
        )
    assert batch.rows_source == 3
    assert batch.rows_imported == 1
    assert batch.rows_unsupported == 2
    assert batch.reconciled
    issues = ImportIssue.objects.filter(batch=batch)
    assert issues.count() == 2
    assert all(i.status == ImportIssue.STATUS_PENDING for i in issues)
    assert {i.line_number for i in issues} == {3, 4}
    assert {i.raw_action for i in issues} == {"Transfer", "Fee Received"}
    assert FinancialEvent.objects.count() == 1


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
