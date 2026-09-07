"""E2E ticket 04 — dividendo com retenção em data distinta: conferir relatório,
corrigir a data documental pelo navegador e ver a trilha de auditoria."""
import pytest

pw = pytest.importorskip("playwright.sync_api")

from tests.e2e.conftest import PASSWORD, cadastrar_ativo, novo_evento


def test_edicao_com_trilha(live_server, page, conta, vault_ready):
    page.goto(f"{live_server}/bloqueado/")
    page.fill("#password", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_url(f"{live_server}/")

    cadastrar_ativo(page, live_server, "AAPL")

    # dividendo 10/03 com imposto pago 12/03
    novo_evento(page, live_server, "DIVIDEND", {
        "trade_date": "2026-03-10", "asset_ticker": "AAPL",
        "quantity": "100", "per_share_usd": "1", "tax_usd": "30",
        "foreign_tax_payment_date": "2026-03-12",
        "date_evidence_source": "BROKER_STATEMENT",
        "country_code": "US", "jurisdiction_level": "FEDERAL",
        "tax_type": "WITHHOLDING_INCOME_TAX",
    })

    # link "imposto" na lista de eventos abre a edição
    page.goto(f"{live_server}/")
    page.locator('a[href^="/imposto-exterior/"]').click()
    page.wait_for_load_state()

    # corrige a data documental com motivo
    page.fill("#id_foreign_tax_payment_date", "2026-03-14")
    page.fill("#id_reason", "Extrato final mostrou pagamento em 14/03")
    page.click("#save-payment")
    page.wait_for_url(f"{live_server}/")

    # trilha visível na página de edição
    page.goto(f"{live_server}/")
    page.locator('a[href^="/imposto-exterior/"]').click()
    page.wait_for_load_state()
    corpo = page.inner_text("body")
    assert "Trilha de auditoria" in corpo
    assert "Extrato final mostrou pagamento em 14/03" in corpo
    assert "2026-03-12 → 2026-03-14" in corpo
