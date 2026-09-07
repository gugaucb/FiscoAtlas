"""Engine Django para SQLite cifrado com SQLCipher (AES-256).

A chave vem da VaultKey em memória (security.state). Se o arquivo ainda é
um banco plaintext (primeira instalação), conecta sem chave.
"""
import re
import sqlite3
from collections.abc import Mapping
from decimal import Decimal
from itertools import tee

from django.db.backends.sqlite3 import base as sqlite_base

SQLITE_HEADER = b"SQLite format 3\x00"
FORMAT_QMARK_REGEX = sqlite_base.FORMAT_QMARK_REGEX


def is_plaintext_or_new(path: str) -> bool:
    """True se o arquivo não existe, é vazio ou é SQLite plaintext (primeira instalação)."""
    try:
        with open(path, "rb") as f:
            head = f.read(16)
        return head == SQLITE_HEADER or head == b""
    except FileNotFoundError:
        return True


def _convert_query(query, *, param_names=None):
    if param_names is None:
        return FORMAT_QMARK_REGEX.sub("?", query).replace("%%", "%")
    return query % {name: f":{name}" for name in param_names}


def make_cursor_wrapper(cursor_cls):
    """Cria um wrapper de cursor com a conversão de placeholders do Django
    (format/pyformat → qmark/named), herdando a classe Cursor do driver.
    Decimais são adaptados para string (o sqlcipher3 não registra o adapter
    que o stdlib sqlite3 recebe do Django)."""

    def _adapt(params):
        if isinstance(params, Mapping):
            return {k: str(v) if isinstance(v, Decimal) else v for k, v in params.items()}
        if isinstance(params, (list, tuple)):
            return type(params)(str(v) if isinstance(v, Decimal) else v for v in params)
        return params

    class Wrapper(cursor_cls):
        def execute(self, query, params=None):
            if params is None:
                return super().execute(query)
            param_names = list(params) if isinstance(params, Mapping) else None
            return super().execute(_convert_query(query, param_names=param_names), _adapt(params))

        def executemany(self, query, param_list):
            param_list = [_adapt(p) for p in param_list]
            peekable, param_list = tee(iter(param_list))
            if (params := next(peekable, None)) and isinstance(params, Mapping):
                param_names = list(params)
            else:
                param_names = None
            return super().executemany(_convert_query(query, param_names=param_names), param_list)

    return Wrapper


class DatabaseWrapper(sqlite_base.DatabaseWrapper):
    # PEP-249 exceptions do sqlcipher3 — permite que o Django traduza erros
    # do driver para django.db.IntegrityError/OperationalError etc.
    import sqlcipher3.dbapi2 as Database

    # mogrify do DEBUG (last_executed_query) também precisa adaptar Decimal
    from security.sqlcipher_backend.operations import SqlcipherOperations as ops_class

    def get_new_connection(self, conn_params):
        import sqlcipher3

        conn = sqlcipher3.connect(**conn_params)
        from django.conf import settings as dj_settings
        from security import state

        # o alias da vault é plaintext (só material wrappado); os demais usam
        # a VaultKey para decifrar
        key = state.get_vault_key() if self.alias != dj_settings.SECURITY_VAULT_ALIAS else None
        if is_plaintext_or_new(conn_params["database"]):
            # primeira instalação: banco plaintext sem setup; chave SQLCipher
            # em arquivo plaintext falharia, então conecta sem chave
            return conn
        if key is None:
            # banco cifrado sem chave em memória: falha explícita
            conn.close()
            raise sqlite3.DatabaseError("Banco cifrado e aplicação bloqueada")
        conn.execute(f"PRAGMA key = \"x'{key.hex()}'\"")
        return conn

    def create_cursor(self, name=None):
        import sqlcipher3

        wrapper_cls = make_cursor_wrapper(sqlcipher3.Cursor)
        return self.connection.cursor(factory=wrapper_cls)