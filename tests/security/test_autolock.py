import pytest
from security.vault import VaultService

pytestmark = pytest.mark.django_db


def test_autolock_apos_inatividade(locked_client, settings):
    settings.AUTO_LOCK_TIMEOUT_MINUTES = 0  # expira imediatamente
    VaultService().setup("S3nh@Forte!")
    locked_client.post("/desbloquear/", {"password": "S3nh@Forte!"})
    # timeout 0: o unlock registra last_activity e a sessão já expirou
    resp = locked_client.get("/")
    assert resp.status_code == 302 and resp.url == "/bloqueado/"


def test_sem_inatividade_continua_aberto(locked_client, settings):
    settings.AUTO_LOCK_TIMEOUT_MINUTES = 10
    VaultService().setup("S3nh@Forte!")
    locked_client.post("/desbloquear/", {"password": "S3nh@Forte!"})
    locked_client.get("/")  # atualiza last_activity
    assert locked_client.get("/").status_code == 200