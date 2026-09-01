import pytest
from security.models import SecurityAuditLog
from security.vault import VaultService

pytestmark = pytest.mark.django_db


@pytest.fixture
def vault_setup():
    svc = VaultService()
    recovery = svc.setup("S3nh@Forte!")
    return recovery


def _lock_page(client):
    return client.get("/bloqueado/")


def test_sem_sessao_todas_as_telas_redirecionam_ao_bloqueio(locked_client):
    resp = locked_client.get("/")
    assert resp.status_code == 302 and resp.url == "/bloqueado/"
    resp = locked_client.get("/apuracao/2026/")
    assert resp.url == "/bloqueado/"


def test_login_pagina_existe(locked_client, vault_setup):
    page = locked_client.get("/bloqueado/").content.decode()
    assert "Senha" in page


def test_desbloqueio_por_senha(locked_client, vault_setup):
    resp = locked_client.post("/desbloquear/", {"password": "S3nh@Forte!"})
    assert resp.status_code == 302
    assert locked_client.get("/").status_code == 200
    log = SecurityAuditLog.objects.filter(event_type="LOGIN_SUCCESS").first()
    assert log is not None
    assert "S3nh@Forte!" not in (log.metadata_safe or {})


def test_desbloqueio_senha_incorreta(locked_client, vault_setup):
    locked_client.post("/desbloquear/", {"password": "errada"})
    resp = locked_client.get("/")
    assert resp.status_code == 302 and resp.url == "/bloqueado/"
    assert SecurityAuditLog.objects.filter(event_type="LOGIN_FAILED").exists()


def test_desbloqueio_por_recovery(locked_client, vault_setup):
    resp = locked_client.post("/desbloquear/", {"recovery_key": vault_setup})
    assert resp.status_code == 302
    assert locked_client.get("/").status_code == 200
    assert SecurityAuditLog.objects.filter(event_type="RECOVERY_USED").exists()


def test_bloqueio_manual(locked_client, vault_setup):
    locked_client.post("/desbloquear/", {"password": "S3nh@Forte!"})
    locked_client.post("/bloquear/")
    assert SecurityAuditLog.objects.filter(event_type="DATABASE_LOCKED").exists()
    resp = locked_client.get("/")
    assert resp.status_code == 302 and resp.url == "/bloqueado/"


def test_primeiro_setup_exibe_recovery_uma_vez(locked_client):
    resp = locked_client.post("/configurar/", {"password": "PrimeiraS3nh@", "password2": "S3nh@errada"})
    assert "não coincidem" in resp.content.decode()
    resp = locked_client.post("/configurar/", {"password": "PrimeiraS3nh@", "password2": "PrimeiraS3nh@"})
    page = resp.content.decode()
    assert "Recovery key" in page and "-" in page
    # já desbloqueado após setup
    assert locked_client.get("/").status_code == 200


def test_setup_senha_curta_rejeitada(locked_client):
    resp = locked_client.post("/configurar/", {"password": "123", "password2": "123"})
    assert "pelo menos 8" in resp.content.decode()


def test_desbloqueio_apos_auto_lock_nao_retrava(locked_client, vault_setup):
    """Regressão: sessão persistente com last_activity velho do auto-lock
    anterior não pode retravar imediatamente após o unlock."""
    from datetime import timedelta

    from django.utils import timezone
    from django.contrib.sessions.backends.signed_cookies import SessionStore

    store = SessionStore()
    store["vault_last_activity"] = (timezone.now() - timedelta(hours=2)).isoformat()
    store.save()
    locked_client.cookies["sessionid"] = store.session_key

    resp = locked_client.post("/desbloquear/", {"password": "S3nh@Forte!"})
    assert resp.status_code == 302
    # não pode voltar imediatamente para /bloqueado/ (auto-lock falso)
    assert locked_client.get("/").status_code == 200


def test_setup_post_na_url_bloqueado_funciona(locked_client):
    """Regressão: a tela de configuração é renderizada em /bloqueado/ e o POST
    do formulário vai para a própria URL — não pode dar 405."""
    resp = locked_client.post("/bloqueado/", {"password": "PrimeiraS3nh@", "password2": "PrimeiraS3nh@"})
    assert resp.status_code == 200
    assert "Recovery key" in resp.content.decode()
    assert locked_client.get("/").status_code == 200


def test_lock_sem_nav_do_app(vault_setup, locked_client):
    """A tela de lock é autônoma: sem abas do app que só redirecionam de volta."""
    page = locked_client.get("/bloqueado/").content.decode()
    assert "/eventos" not in page
    assert "/posicoes" not in page
    assert "Bloquear" not in page
    assert 'action="/desbloquear/"' in page


def test_setup_sem_nav_do_app(locked_client):
    from security.vault import VaultService
    from security.models import SecuritySettings
    SecuritySettings.objects.all().delete()
    assert not VaultService().is_configured()
    page = locked_client.get("/bloqueado/").content.decode()
    assert "/eventos" not in page
    assert "/posicoes" not in page
    assert 'action="/configurar/"' in page
