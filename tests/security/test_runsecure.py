"""runsecure: runserver que sobe travado (desbloqueio 100% via navegador)."""
import pytest
from django.core.management import call_command

from security import state

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _vault_pronta():
    from security.vault import VaultService

    if not VaultService().is_configured():
        VaultService().setup("test-password-123")
    state.clear_vault_key()
    yield
    state.clear_vault_key()


def test_check_migrations_e_no_op(monkeypatch):
    """O override deve valer por si: mesmo se o pai tocar o banco, o filho não."""
    from django.core.management.commands.runserver import Command as Parent

    def boom(self):
        raise AssertionError("check_migrations do pai foi chamado")

    monkeypatch.setattr(Parent, "check_migrations", boom)
    from security.management.commands.runsecure import Command

    Command().check_migrations()  # não deve propagar


def test_sobe_travado_sem_pedir_senha(monkeypatch):
    """handle → inner_run sem chave em memória e sem getpass."""
    import security.management.commands.runsecure as mod

    calls = {}

    def fake_inner_run(self, *args, **options):
        calls["key"] = state.get_vault_key()
        calls["use_reloader"] = options.get("use_reloader")

    monkeypatch.setattr(mod.Command, "inner_run", fake_inner_run)
    call_command("runsecure", "127.0.0.1:8000")
    assert calls["key"] is None
    assert calls["use_reloader"] is False
