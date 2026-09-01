"""Criptografia do banco principal com SQLCipher.

Converte um banco SQLite plaintext para o formato cifrado via
sqlcipher_export (receita oficial de migração one-time), preservando dados.
"""
import os
import tempfile

import sqlcipher3


def rekey_main_database(source_path: str, dest_path: str, vault_key: bytes) -> None:
    """Exporta o banco plaintext para um novo arquivo cifrado com a VaultKey."""
    if os.path.exists(dest_path):
        os.remove(dest_path)
    conn = sqlcipher3.connect(source_path)
    try:
        conn.execute(f"ATTACH DATABASE '{dest_path}' AS encrypted KEY \"x'{vault_key.hex()}'\"")
        conn.execute("SELECT sqlcipher_export('encrypted')")
        conn.execute("DETACH DATABASE encrypted")
    finally:
        conn.close()


def encrypt_database_copy(source_path: str, vault_key: bytes) -> str:
    """Retorna o caminho de um arquivo cifrado temporário do banco."""
    dest = tempfile.mktemp(suffix=".enc.db")
    rekey_main_database(source_path, dest, vault_key)
    return dest