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
