import pytest

from security.audit import verify_chain
from security.models import SecurityAuditLog
from security.state import clear_vault_key, set_vault_key
from security.vault import InvalidPassword, VaultService

pytestmark = pytest.mark.django_db

PASSWORD = "SenhaAtual123"


@pytest.fixture
def unlocked():
    svc = VaultService()
    recovery = svc.setup(PASSWORD)
    key = svc.unlock_with_password(PASSWORD)
    set_vault_key(key)
    yield svc, key, recovery
    clear_vault_key()


def test_regenerar_recovery_service(unlocked):
    svc, key, recovery_antiga = unlocked

    nova = svc.regenerate_recovery_key(key)

    # formato: 6 grupos de 4, separados por hífen
    assert nova.count("-") == 5 and all(len(p) == 4 for p in nova.split("-"))
    assert nova != recovery_antiga
    # nova recovery abre a mesma vault key
    assert svc.unlock_with_recovery(nova) == key
    # antiga deixa de valer
    with pytest.raises(InvalidPassword):
        svc.unlock_with_recovery(recovery_antiga)
    # senha continua válida
    assert svc.unlock_with_password(PASSWORD) == key


def test_regenerar_view_fluxo_completo(client):
    # conftest: client já chega com vault configurada e desbloqueada (TEST_PASSWORD)
    resp = client.get("/seguranca/")
    page = resp.content.decode()
    assert "Recovery" in page

    resp = client.post("/seguranca/recovery/regenerar/")
    assert resp.status_code == 200
    page = resp.content.decode()
    import re

    match = re.search(r"\b[23456789A-HJ-NP-Z]{4}(?:-[23456789A-HJ-NP-Z]{4}){5}\b", page)
    assert match, "recovery key não exibida no corpo"
    nova = match.group(0)
    # evento de auditoria sem a chave no metadata
    log = SecurityAuditLog.objects.filter(event_type="RECOVERY_REGENERATED").first()
    assert log is not None
    assert nova not in str(log.metadata_safe)
    assert verify_chain()

    # nova recovery realmente desbloqueia
    assert client.post("/desbloquear/", {"recovery_key": nova}).status_code == 302


def test_regenerar_travado_redireciona(locked_client):
    resp = locked_client.post("/seguranca/recovery/regenerar/")
    assert resp.status_code == 302 and resp.url == "/bloqueado/"
