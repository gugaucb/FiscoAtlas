import sqlite3

import pytest

from security.database import rekey_main_database
from security.state import clear_vault_key, set_vault_key

pytestmark = pytest.mark.django_db


@pytest.fixture
def vault_key():
    from security.vault import VaultService

    svc = VaultService()
    if not svc.is_configured():
        svc.setup("test-password-123")
    key = svc.unlock_with_password("test-password-123")
    set_vault_key(key)
    yield key
    clear_vault_key()


def _make_plaintext_db(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    conn.execute("INSERT INTO t (v) VALUES ('dado fiscal')")
    conn.commit()
    conn.close()


def test_criptografia_banco_plaintext_roda_sem_erro(tmp_path, vault_key):
    """Regressão: UnboundLocalError ('os' usado antes do import) no setup real."""
    from security.views import _encrypt_main_database

    db_path = str(tmp_path / "db.sqlite3")
    _make_plaintext_db(db_path)

    _encrypt_main_database(db_path)

    raw = open(db_path, "rb").read()
    assert not raw.startswith(b"SQLite format 3")  # agora cifrado
    # legível com a VaultKey e dados intactos
    import sqlcipher3

    conn = sqlcipher3.connect(db_path)
    conn.execute(f"PRAGMA key = \"x'{vault_key.hex()}'\"")
    assert conn.execute("SELECT v FROM t").fetchone()[0] == "dado fiscal"
    conn.close()


def test_banco_ja_cifrado_nao_é_reprocessado(tmp_path, vault_key):
    from security.sqlcipher_backend.base import is_plaintext_or_new
    from security.views import _encrypt_main_database

    db_path = str(tmp_path / "db.sqlite3")
    _make_plaintext_db(str(tmp_path / "orig.sqlite3"))
    rekey_main_database(str(tmp_path / "orig.sqlite3"), db_path, vault_key)
    before = open(db_path, "rb").read()
    assert not is_plaintext_or_new(db_path)

    _encrypt_main_database(db_path)

    assert open(db_path, "rb").read() == before  # inalterado
