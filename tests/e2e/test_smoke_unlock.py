"""E2E com browser real (Playwright) contra o LiveServer do Django.

O LiveServer roda no mesmo processo: a VaultKey setada pelo unlock via
HTTP fica visível para todas as threads (security.state é module-level).
"""
import pytest

pw = pytest.importorskip("playwright.sync_api")

from tests.e2e.conftest import PASSWORD  # noqa: F401


def test_desbloqueio_no_browser_real(live_server, page, vault_ready):
    page.goto(f"{live_server}/bloqueado/")
    assert page.locator("h1").inner_text() == "Aplicação bloqueada"

    page.fill("#password", PASSWORD)
    page.click("button[type=submit]")

    page.wait_for_url(f"{live_server}/")
    assert "Novo lançamento" in page.content()
    # abas acessíveis
    page.click("text=Posições")
    page.wait_for_url(f"{live_server}/posicoes/")
    assert page.locator("h1").inner_text()
