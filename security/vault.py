"""Vault: envelope encryption local.

senha → Argon2id → KEK → unwrap VaultKey (256 bits CSPRNG).
A senha NUNCA é usada diretamente como chave. Troca de senha = rewrap.
"""
import secrets

from argon2.low_level import Type, hash_secret_raw

from security.crypto import CryptoProvider
from security.models import SecuritySettings

_RECOVERY_GROUPS = 6
_RECOVERY_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"  # sem I/L/O/0/1


class VaultLocked(Exception):
    """Vault não configurada ainda."""


class InvalidPassword(Exception):
    """Senha ou recovery key incorreta."""


def _argon2id(password: bytes, salt: bytes, memory_cost: int, iterations: int, parallelism: int) -> bytes:
    return hash_secret_raw(
        secret=password, salt=salt, time_cost=iterations,
        memory_cost=memory_cost, parallelism=parallelism,
        hash_len=32, type=Type.ID,
    )


def _recovery_key() -> str:
    raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(_RECOVERY_GROUPS * 4))
    return "-".join(raw[i:i + 4] for i in range(0, len(raw), 4))


class VaultService:
    def __init__(self):
        self._provider = CryptoProvider()

    def is_configured(self) -> bool:
        s = SecuritySettings.get()
        return bool(s and s.wrapped_vault_key_password)

    def setup(self, password: str) -> str:
        """Primeiro acesso: gera VaultKey + recovery key. Retorna a recovery
        key para exibição única ao usuário."""
        if SecuritySettings.get() is not None:
            raise Exception("Vault já configurada")
        salt = secrets.token_bytes(16)
        vault_key = self._provider.generate_key()
        recovery = _recovery_key()
        kek_password = _argon2id(password.encode(), salt, 65536, 3, 4)
        kek_recovery = _argon2id(recovery.encode(), salt, 65536, 3, 4)
        SecuritySettings.objects.create(
            argon2_salt=salt,
            wrapped_vault_key_password=self._provider.wrap_key(kek_password, vault_key),
            wrapped_vault_key_recovery=self._provider.wrap_key(kek_recovery, vault_key),
        )
        return recovery

    def _settings(self) -> SecuritySettings:
        s = SecuritySettings.get()
        if s is None:
            raise VaultLocked("Vault não configurada")
        return s

    def _wrap_with_password(self, password: str, salt: bytes, vault_key: bytes) -> bytes:
        s = SecuritySettings.get()
        mem = s.argon2_memory_cost if s else 65536
        it = s.argon2_iterations if s else 3
        par = s.argon2_parallelism if s else 4
        kek = _argon2id(password.encode(), salt, mem, it, par)
        return self._provider.wrap_key(kek, vault_key)

    def _wrap_with_recovery(self, recovery: str, vault_key: bytes, salt: bytes = None) -> bytes:
        s = SecuritySettings.get()
        kek = _argon2id(recovery.encode(), salt if salt is not None else bytes(s.argon2_salt),
                        s.argon2_memory_cost if s else 65536,
                        s.argon2_iterations if s else 3,
                        s.argon2_parallelism if s else 4)
        return self._provider.wrap_key(kek, vault_key)

    def unlock_with_password(self, password: str) -> bytes:
        s = self._settings()
        kek = _argon2id(password.encode(), bytes(s.argon2_salt),
                        s.argon2_memory_cost, s.argon2_iterations, s.argon2_parallelism)
        try:
            return self._provider.unwrap_key(kek, bytes(s.wrapped_vault_key_password))
        except Exception as e:
            raise InvalidPassword("Senha incorreta") from e

    def unlock_with_recovery(self, recovery: str) -> bytes:
        s = self._settings()
        kek = _argon2id(recovery.strip().encode(), bytes(s.argon2_salt),
                        s.argon2_memory_cost, s.argon2_iterations, s.argon2_parallelism)
        try:
            return self._provider.unwrap_key(kek, bytes(s.wrapped_vault_key_recovery))
        except Exception as e:
            raise InvalidPassword("Recovery key incorreta") from e

    def change_password(self, old_password: str, new_password: str) -> None:
        vault_key = self.unlock_with_password(old_password)
        s = self._settings()
        s.wrapped_vault_key_password = self._wrap_with_password(new_password, bytes(s.argon2_salt), vault_key)
        s.save(update_fields=["wrapped_vault_key_password", "updated_at"])

    def recover(self, recovery: str, new_password: str) -> None:
        vault_key = self.unlock_with_recovery(recovery)
        s = self._settings()
        s.wrapped_vault_key_password = self._wrap_with_password(new_password, bytes(s.argon2_salt), vault_key)
        s.save(update_fields=["wrapped_vault_key_password", "updated_at"])

    def regenerate_recovery_key(self, vault_key: bytes) -> str:
        """Nova recovery key substitui a antiga (rewrap da VaultKey).
        A senha permanece válida. Retorna a chave para exibição única."""
        recovery = _recovery_key()
        s = self._settings()
        s.wrapped_vault_key_recovery = self._wrap_with_recovery(recovery, vault_key)
        s.save(update_fields=["wrapped_vault_key_recovery", "updated_at"])
        return recovery
