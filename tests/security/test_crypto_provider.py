import pytest
from security.crypto import CryptoProvider, CryptoError


def test_roundtrip():
    provider = CryptoProvider()
    key = provider.generate_key()
    ct = provider.encrypt(key, b"segredo fiscal")
    assert provider.decrypt(key, ct) == b"segredo fiscal"


def test_nonce_unico_ciphertext_diferente():
    provider = CryptoProvider()
    key = provider.generate_key()
    ct1 = provider.encrypt(key, b"mesma entrada")
    ct2 = provider.encrypt(key, b"mesma entrada")
    assert ct1 != ct2


def test_tampering_falha_autenticacao():
    provider = CryptoProvider()
    key = provider.generate_key()
    ct = bytearray(provider.encrypt(key, b"dados"))
    ct[10] ^= 0xFF
    with pytest.raises(CryptoError):
        provider.decrypt(key, bytes(ct))


def test_chave_errada_falha():
    provider = CryptoProvider()
    ct = provider.encrypt(provider.generate_key(), b"dados")
    with pytest.raises(CryptoError):
        provider.decrypt(provider.generate_key(), ct)


def test_crypto_version_no_formato():
    provider = CryptoProvider()
    ct = provider.encrypt(provider.generate_key(), b"x")
    assert provider.CRYPTO_VERSION == 1
    assert ct[:1] == b"\x01"  # byte de versão no início do envelope


def test_wrap_unwrap_chave():
    provider = CryptoProvider()
    vault_key = provider.generate_key()
    file_key = provider.generate_key()
    wrapped = provider.wrap_key(vault_key, file_key)
    assert provider.unwrap_key(vault_key, wrapped) == file_key
    with pytest.raises(CryptoError):
        provider.unwrap_key(provider.generate_key(), wrapped)
