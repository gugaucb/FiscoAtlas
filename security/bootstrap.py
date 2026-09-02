"""Autocorreção pós-desbloqueio.

Com o banco principal cifrado, entrypoint não consegue rodar migrations/seed
em banco existente (a VaultKey só existe na memória do processo do servidor).
Rodamos migrate + seed dentro do próprio processo, uma única vez, logo após
o primeiro desbloqueio — quando a chave já está em memória.
"""

_done = False


def bootstrap_pos_unlock() -> bool:
    """Executa migrations (default + vault) e seed_tax_rules uma vez por processo.

    Retorna True se executou; False se já tinha rodado (no-op).
    """
    global _done
    if _done:
        return False
    from django.conf import settings

    if getattr(settings, "SECURITY_VAULT_ALIAS", "vault") == "default":
        _done = True  # ambiente de teste: bancos in-memory já migrados
        return False
    from django.core.management import call_command

    from security.views import _close_db_connections

    _close_db_connections()  # reconecta com PRAGMA key
    call_command("migrate", interactive=False, verbosity=0)
    call_command("migrate", database="vault", interactive=False, verbosity=0)
    call_command("seed_tax_rules", verbosity=0)
    _done = True
    return True
