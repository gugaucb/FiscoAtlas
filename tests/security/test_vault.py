import base64
import pytest
from security.models import SecuritySettings
from security.vault import VaultService, VaultLocked, InvalidPassword

pytestmark = pytest.mark.django_db


def test_setup_inicial_gera_vaultkey_e_recovery():
    svc = VaultService()
    recovery = svc.setup("MinhaS3nh@forte")
    # recovery exibida uma única vez, formato XXXX-XXXX-...
    assert recovery.count("-") == 5
    assert all(len(p) == 4 for p in recovery.split("-"))
    settings = SecuritySettings.get()
    assert settings.wrapped_vault_key_password
    assert settings.wrapped_vault_key_recovery
    # nenhuma chave em plaintext: o modelo nem tem campo para vault_key/recovery
    assert not hasattr(settings, "vault_key")
    assert not hasattr(settings, "recovery_key")
    assert settings.argon2_salt
    assert settings.argon2_memory_cost > 0


def test_desbloqueio_por_senha_correta():
    svc = VaultService()
    svc.setup("MinhaS3nh@forte")
    vault_key = svc.unlock_with_password("MinhaS3nh@forte")
    assert len(vault_key) == 32


def test_senha_incorreta_falha():
    svc = VaultService()
    svc.setup("MinhaS3nh@forte")
    with pytest.raises(InvalidPassword):
        svc.unlock_with_password("errada")


def test_desbloqueio_por_recovery_key():
    svc = VaultService()
    recovery = svc.setup("MinhaS3nh@forte")
    vault_key = svc.unlock_with_recovery(recovery)
    assert vault_key == svc.unlock_with_password("MinhaS3nh@forte")


def test_recovery_incorreta_falha():
    svc = VaultService()
    svc.setup("MinhaS3nh@forte")
    with pytest.raises(InvalidPassword):
        svc.unlock_with_recovery("AAAA-BBBB-CCCC-DDDD-EEEE-FFFF")


def test_troca_de_senha_reambula_sem_recriptografar():
    svc = VaultService()
    svc.setup("SenhaAntiga123")
    original_vault_key = svc.unlock_with_password("SenhaAntiga123")
    wrapped_before = SecuritySettings.get().wrapped_vault_key_password

    svc.change_password("SenhaAntiga123", "NovaSenha456")

    # conteúdo protegido continua decifrável pela mesma VaultKey
    assert svc.unlock_with_password("NovaSenha456") == original_vault_key
    # wrapper foi re-gerado (nova KEK)
    assert SecuritySettings.get().wrapped_vault_key_password != wrapped_before
    with pytest.raises(InvalidPassword):
        svc.unlock_with_password("SenhaAntiga123")


def test_recuperacao_redefine_senha():
    svc = VaultService()
    recovery = svc.setup("SenhaAntiga123")
    original_vault_key = svc.unlock_with_password("SenhaAntiga123")

    svc.recover(recovery, "NovaSenha789")

    assert svc.unlock_with_password("NovaSenha789") == original_vault_key


def test_setup_duas_vezes_nao_duplica():
    svc = VaultService()
    svc.setup("Senha1")
    with pytest.raises(Exception):
        svc.setup("Senha2")
    assert SecuritySettings.objects.count() == 1


def test_vault_sem_setup_fica_travada():
    with pytest.raises(VaultLocked):
        VaultService().unlock_with_password("qualquer")
