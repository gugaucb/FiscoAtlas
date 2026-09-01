"""Lock real: sessão não vale desbloqueio sem a VaultKey em memória."""
import pytest

from django.test import RequestFactory

from security import state
from security.middleware import LAST_ACTIVITY_KEY, UNLOCKED_KEY, VaultLockMiddleware

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def chave_limpa():
    state.clear_vault_key()
    yield
    state.clear_vault_key()


class FakeSession(dict):
    def cycle_key(self):
        pass


def _request():
    from django.utils import timezone

    agora = timezone.now().isoformat()
    req = RequestFactory().get("/")
    req.session = FakeSession({UNLOCKED_KEY: agora, LAST_ACTIVITY_KEY: agora})
    return req


def test_sessao_unlocked_sem_chave_em_memoria_redireciona():
    # simula container reiniciado: cookie diz desbloqueado, memória não tem chave
    resp = VaultLockMiddleware(lambda r: pytest.fail("não deveria passar")).__call__(_request())
    assert resp.status_code == 302
    assert resp.url == "/bloqueado/"


def test_sessao_unlocked_com_chave_em_memoria_passa(monkeypatch):
    state.set_vault_key(b"\x01" * 32)
    passado = []
    resp = VaultLockMiddleware(lambda r: passado.append(1) or "ok").__call__(_request())
    assert passado == [1]


def test_sessao_limpa_apos_detectar_reinicio():
    req = _request()
    resp = VaultLockMiddleware(lambda r: None).__call__(req)
    assert UNLOCKED_KEY not in req.session
