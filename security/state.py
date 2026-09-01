"""Estado volátil da VaultKey em memória do processo.

A VaultKey NUNCA vai para disco, sessão, log ou frontend. Vive só aqui
enquanto a aplicação está desbloqueada; bloquear limpa a referência.
"""
_vault_key: bytes | None = None


def set_vault_key(key: bytes) -> None:
    global _vault_key
    _vault_key = key


def get_vault_key() -> bytes | None:
    return _vault_key


def clear_vault_key() -> None:
    global _vault_key
    if _vault_key:
        # melhor esforço: não é zerável com garantia em Python, mas removemos a referência
        _vault_key = b"\x00" * len(_vault_key)
    _vault_key = None