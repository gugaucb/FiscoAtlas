"""Documentos cifrados em repouso: FileKey aleatória por arquivo, AES-256-GCM,
FileKey wrappada pela VaultKey. O original nunca toca o disco em plaintext."""
import hashlib
import os
import secrets

from django.conf import settings

from security.crypto import CryptoProvider
from security.models import EncryptedDocument


class EncryptedFileService:
    def __init__(self):
        self._provider = CryptoProvider()
        self.storage_dir = getattr(settings, "DOCUMENT_STORAGE_PATH", "documents")
        os.makedirs(self.storage_dir, exist_ok=True)

    def store(self, filename: str, content: bytes) -> "EncryptedDocument":
        from security import state

        vault_key = state.get_vault_key()
        if vault_key is None:
            raise RuntimeError("Aplicação bloqueada: VaultKey indisponível")
        file_key = self._provider.generate_key()
        envelope = self._provider.encrypt(file_key, content)
        wrapped_file_key = self._provider.wrap_key(vault_key, file_key)
        file_id = secrets.token_hex(12)
        path = os.path.join(self.storage_dir, f"{file_id}.enc")
        with open(path, "wb") as f:
            f.write(envelope)
        doc = EncryptedDocument.objects.create(
            encrypted_filename=self._provider.encrypt(file_key, filename.encode()),
            wrapped_file_key=wrapped_file_key,
            file_path=path,
            file_hash=hashlib.sha256(content).hexdigest(),
            crypto_version=self._provider.CRYPTO_VERSION,
        )
        return doc

    def read(self, doc: "EncryptedDocument") -> bytes:
        from security import state

        vault_key = state.get_vault_key()
        if vault_key is None:
            raise RuntimeError("Aplicação bloqueada: VaultKey indisponível")
        file_key = self._provider.unwrap_key(vault_key, bytes(doc.wrapped_file_key))
        with open(doc.file_path, "rb") as f:
            envelope = f.read()
        return self._provider.decrypt(file_key, envelope)

    def read_filename(self, doc: "EncryptedDocument") -> str:
        from security import state

        file_key = self._provider.unwrap_key(state.get_vault_key(), bytes(doc.wrapped_file_key))
        return self._provider.decrypt(file_key, bytes(doc.encrypted_filename)).decode()