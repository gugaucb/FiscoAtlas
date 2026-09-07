"""Operations do backend SQLCipher.

O sqlcipher3 não registra o adapter de Decimal que o stdlib sqlite3 recebe
do Django (ticket 08). O wrapper de cursor adapta os parâmetros no execute,
mas com DEBUG=True o django.db.backends.utils.debug_sql chama
operations.last_executed_query, que faz mogrify dos parâmetros BRUTOS em um
cursor cru do driver — quebrando com InterfaceError em qualquer lookup com
Decimal. A sanitização é replicada aqui.
"""
from decimal import Decimal

from django.db.backends.sqlite3 import operations as sqlite_operations


def _sanitize(params):
    if isinstance(params, (list, tuple)):
        return type(params)(
            str(v) if isinstance(v, Decimal) else v
            for v in params
        )
    if isinstance(params, dict):
        return {
            k: (str(v) if isinstance(v, Decimal) else v)
            for k, v in params.items()
        }
    return params


class SqlcipherOperations(sqlite_operations.DatabaseOperations):
    def last_executed_query(self, cursor, sql, params):
        return super().last_executed_query(cursor, sql, _sanitize(params))
