import os
import sqlite3
import tempfile

import pytest
from security.database import rekey_main_database, encrypt_database_copy
from security.state import clear_vault_key, get_vault_key, set_vault_key

KEY = bytes(range(32))


@pytest.fixture(autouse=True)
def _clean_state():
    clear_vault_key()
    yield
    clear_vault_key()


def _plaintext_db(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE dados (v TEXT)")
    conn.execute("INSERT INTO dados VALUES ('cpf-123')")
    conn.commit()
    conn.close()


def test_rekey_torna_banco_ilegivel_sem_chave():
    src = tempfile.mktemp(suffix=".db")
    dst = tempfile.mktemp(suffix=".db")
    _plaintext_db(src)

    rekey_main_database(src, dst, KEY)

    # sem chave: sqlite3 puro não abre
    with pytest.raises(sqlite3.DatabaseError):
        conn = sqlite3.connect(dst)
        conn.execute("SELECT * FROM dados")
    # sem chave: cabeçalho não é mais SQLite plaintext
    with open(dst, "rb") as f:
        assert f.read(16) != b"SQLite format 3\x00"
    # com a chave correta: dados preservados
    import sqlcipher3
    conn = sqlcipher3.connect(dst)
    conn.execute(f"PRAGMA key = \"x'{KEY.hex()}'\"")
    assert conn.execute("SELECT v FROM dados").fetchone() == ("cpf-123",)
    conn.close()


def test_banco_copiado_permanece_cifrado():
    src = tempfile.mktemp(suffix=".db")
    dst = tempfile.mktemp(suffix=".db")
    _plaintext_db(src)
    rekey_main_database(src, dst, KEY)
    copia = tempfile.mktemp(suffix=".db")
    with open(dst, "rb") as f:
        data = f.read()
    with open(copia, "wb") as f:
        f.write(data)
    import sqlcipher3
    conn = sqlcipher3.connect(copia)
    conn.execute(f"PRAGMA key = \"x'{KEY.hex()}'\"")
    assert conn.execute("SELECT v FROM dados").fetchone() == ("cpf-123",)
    conn.close()


def test_chave_errada_nao_abre():
    src = tempfile.mktemp(suffix=".db")
    dst = tempfile.mktemp(suffix=".db")
    _plaintext_db(src)
    rekey_main_database(src, dst, KEY)
    import sqlcipher3
    conn = sqlcipher3.connect(dst)
    conn.execute(f"PRAGMA key = \"x'{(KEY[::-1]).hex()}'\"")
    with pytest.raises(Exception):
        conn.execute("SELECT count(*) FROM dados").fetchone()
    conn.close()


def test_state_limpa_chave():
    set_vault_key(KEY)
    assert get_vault_key() == KEY
    clear_vault_key()
    assert get_vault_key() is None