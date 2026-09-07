import pytest

from security.vault import VaultService

TEST_PASSWORD = "test-password-123"


@pytest.fixture
def client(client, db):
    """Client do pytest-django com o vault configurado e a aplicação desbloqueada."""
    svc = VaultService()
    if not svc.is_configured():
        svc.setup(TEST_PASSWORD)
    client.post("/desbloquear/", {"password": TEST_PASSWORD})
    return client


@pytest.fixture
def residente(db):
    """Perfil residente fiscal pleno (RF-PER-001): pré-condição de apuração."""
    from fiscal.models import Profile

    return Profile.objects.create(
        name="Gustavo", cpf="000.000.000-00", tax_residency_status="BRAZIL_RESIDENT"
    )
