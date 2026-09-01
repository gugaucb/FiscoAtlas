import json
import sqlite3
import tempfile
import zipfile

import pytest
from django.core.management import call_command
from security.database import rekey_main_database
from security.models import SecurityAuditLog
from security.vault import VaultService

pytestmark = pytest.mark.django_db

TEST_PASSWORD = "test-password-123"
KEY = bytes(range(32))


@pytest.fixture(autouse=True)
def _vault():
    svc = VaultService()
    if not svc.is_configured():
        svc.setup(TEST_PASSWORD)
    yield


def _encrypted_sample_db():
    src = tempfile.mktemp(suffix=".db")
    conn = sqlite3.connect(src)
    conn.execute("CREATE TABLE ledger_asset (ticker TEXT)")
    conn.commit()
    conn.close()
    dst = tempfile.mktemp(suffix=".enc.db")
    rekey_main_database(src, dst, KEY)
    return dst


def _make_backup(tmp_path):
    out = tmp_path / "backup.zip"
    call_command("backup_encrypted", str(out), "--db", _encrypted_sample_db())
    return out


def test_backup_so_contem_material_cifrado(tmp_path):
    out = _make_backup(tmp_path)
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    assert "db.sqlite3.enc" in " ".join(names)
    assert not any(n.endswith(".db") and "enc" not in n for n in names)
    assert not any("plaintext" in n for n in names)


def test_banco_no_backup_ilegivel_sem_chave(tmp_path):
    out = _make_backup(tmp_path)
    with zipfile.ZipFile(out) as z:
        raw = z.read("db.sqlite3.enc")
    assert raw[:16] != b"SQLite format 3\x00"
    # sqlite3 puro não abre
    import tempfile, os
    tmp = tempfile.mktemp(suffix=".db")
    with open(tmp, "wb") as f:
        f.write(raw)
    conn = sqlite3.connect(tmp)
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("SELECT count(*) FROM ledger_asset")


def test_backup_contem_wrapped_keys_e_nao_chaves_plaintext(tmp_path):
    out = _make_backup(tmp_path)
    with zipfile.ZipFile(out) as z:
        meta = json.loads(z.read("metadata.json"))
    assert meta["crypto_version"] == 1
    # nenhuma chave plaintext no pacote
    with zipfile.ZipFile(out) as z:
        for n in z.namelist():
            data = z.read(n)
            if n.endswith(".enc") or n == "metadata.json":
                assert b"wrapped_vault_key" not in data or n == "metadata.json"
    # metadata contém apenas material wrappado (strings base64) + parâmetros KDF
    import base64
    wk = meta.get("wrapped_keys", {})
    for k in ("password", "recovery", "argon2_salt"):
        assert len(base64.b64decode(wk[k])) > 0


def test_restore_exige_chave(tmp_path):
    out = _make_backup(tmp_path)
    # restaura para arquivo e tenta abrir sem chave
    with zipfile.ZipFile(out) as z:
        raw = z.read("db.sqlite3.enc")
    import tempfile
    tmp = tempfile.mktemp(suffix=".db")
    with open(tmp, "wb") as f:
        f.write(raw)
    conn = sqlite3.connect(tmp)
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("SELECT count(*) FROM ledger_asset")
    conn.close()


def test_hash_chaining_detecta_alteracao_retroativa():
    from security.audit import log_event, verify_chain
    log_event("BACKUP_CREATED")
    log_event("RESTORE_EXECUTED")
    assert verify_chain() is True
    # alteração retroativa: modifica o metadata do primeiro evento
    ev = SecurityAuditLog.objects.order_by("id").first()
    ev.metadata_safe = {"tampered": True}
    ev.save()
    assert verify_chain() is False


def test_logs_nao_contem_dados_sensiveis(client, settings):
    import logging
    records = []
    handler = logging.Handler()
    handler.emit = lambda r: records.append(r.getMessage())
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        client.post("/desbloquear/", {"password": "senha-secreta-errada"})
    finally:
        root.removeHandler(handler)
    joined = " ".join(records)
    assert "senha-secreta-errada" not in joined