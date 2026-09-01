import base64
import os
import tempfile
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from security.documents import EncryptedFileService
from security.models import EncryptedDocument
from security.state import set_vault_key
from security.vault import VaultService

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.4 informe avenue 2026 com dados fiscais"


@pytest.fixture(autouse=True)
def _unlocked():
    from security.vault import VaultService
    svc = VaultService()
    if not svc.is_configured():
        svc.setup("test-password-123")
    set_vault_key(svc.unlock_with_password("test-password-123"))
    yield
    from security.state import clear_vault_key
    clear_vault_key()


def test_upload_salva_cifrado_sem_plaintext_no_disco(client):
    upload = SimpleUploadedFile("informe_avenue_2026.pdf", PDF, content_type="application/pdf")
    resp = client.post("/documentos/", {"file": upload})
    assert resp.status_code == 302
    doc = EncryptedDocument.objects.first()
    assert doc is not None
    # no disco: o arquivo do documento é .enc e ilegível
    enc = Path(doc.file_path)
    assert enc.suffix == ".enc"
    raw = enc.read_bytes()
    assert b"informe" not in raw
    assert b"%PDF" not in raw
    assert raw[:1] == b"\x01"  # envelope crypto v1
    # nenhum plaintext do upload espalhado no diretório de storage
    for f in Path(os.path.dirname(doc.file_path)).iterdir():
        if f.suffix != ".enc":
            assert "informe" not in f.read_bytes().decode("utf-8", errors="ignore")
    # metadata: nome nunca em plaintext
    assert b"informe" not in bytes(doc.encrypted_filename or b"")


def test_download_descriptografa_on_the_fly(client):
    upload = SimpleUploadedFile("informe_avenue_2026.pdf", PDF, content_type="application/pdf")
    client.post("/documentos/", {"file": upload})
    doc = EncryptedDocument.objects.first()
    resp = client.get(f"/documentos/{doc.pk}/download/")
    assert resp.status_code == 200
    assert resp.content == PDF
    assert "informe_avenue_2026.pdf" in resp["Content-Disposition"]


def test_arquivo_adulterado_falha_download(client):
    upload = SimpleUploadedFile("extrato.csv", b"data,ticker\n2026-01-01,AAPL", content_type="text/csv")
    client.post("/documentos/", {"file": upload})
    doc = EncryptedDocument.objects.first()
    enc = Path(doc.file_path)
    data = bytearray(enc.read_bytes())
    data[20] ^= 0xFF
    enc.write_bytes(bytes(data))
    resp = client.get(f"/documentos/{doc.pk}/download/")
    assert resp.status_code == 200
    assert "corrompido" in resp.content.decode() or "inválido" in resp.content.decode()


def test_service_roundtrip_sem_view():
    svc = EncryptedFileService()
    doc = svc.store("informe.pdf", PDF)
    assert svc.read(doc) == PDF
    assert doc.file_hash == __import__("hashlib").sha256(PDF).hexdigest()


def test_nome_cifrado_no_banco_e_exibido_para_usuario_desbloqueado(client):
    upload = SimpleUploadedFile("extrato_secreto.csv", b"a,b", content_type="text/csv")
    client.post("/documentos/", {"file": upload})
    doc = EncryptedDocument.objects.first()
    # no banco: nome nunca em plaintext
    assert b"extrato_secreto" not in bytes(doc.encrypted_filename)
    # na tela desbloqueada: nome visível para o dono
    page = client.get("/documentos/").content.decode()
    assert "extrato_secreto.csv" in page
    assert "Documento" in page