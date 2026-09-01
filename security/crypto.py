"""Provedor criptográfico do sistema (crypto agility: ponto único de troca de algoritmo).

Formato do envelope: [version:1][nonce:12][ciphertext+tag:16].
Sempre AES-256-GCM autenticado (nunca ECB/CBC sem tag).
"""
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

CRYPTO_VERSION = 1
_NONCE_SIZE = 12


class CryptoError(Exception):
    """Falha de criptografia: tag inválida, chave errada ou formato inválido."""


class CryptoProvider:
    CRYPTO_VERSION = CRYPTO_VERSION

    def generate_key(self) -> bytes:
        return AESGCM.generate_key(bit_length=256)  # CSPRNG

    def encrypt(self, key: bytes, plaintext: bytes) -> bytes:
        nonce = os.urandom(_NONCE_SIZE)
        ct = AESGCM(key).encrypt(nonce, plaintext, None)
        return bytes([CRYPTO_VERSION]) + nonce + ct

    def decrypt(self, key: bytes, envelope: bytes) -> bytes:
        try:
            version, nonce, ct = envelope[:1], envelope[1:13], envelope[13:]
            if version[0] != CRYPTO_VERSION:
                raise CryptoError(f"Versão de criptografia desconhecida: {version[0]}")
            return AESGCM(key).decrypt(nonce, ct, None)
        except (InvalidTag, IndexError, ValueError) as e:
            raise CryptoError("Falha de autenticação: dados corrompidos ou chave errada") from e

    def wrap_key(self, wrapping_key: bytes, key_to_wrap: bytes) -> bytes:
        """Embrulha uma chave com outra (padrão envelope)."""
        return self.encrypt(wrapping_key, key_to_wrap)

    def unwrap_key(self, wrapping_key: bytes, wrapped: bytes) -> bytes:
        return self.decrypt(wrapping_key, wrapped)
