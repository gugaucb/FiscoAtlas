"""E2E browser: preencher os 8 tipos de evento no form real e validar abas."""
import re

import pytest

pw = pytest.importorskip("playwright.sync_api")

from tests.e2e.conftest import PASSWORD, cadastrar_ativo

PTAX = {"ptax_manual": "5.4000", "ptax_reason": "E2E: API fora"}


def _login(page, live_server):
    page.goto(f"{live_server}/bloqueado/")
    page.fill("#password", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_url(f"{live_server}/")


def _evento(page, live_server, etype, campos, conta_label="Avenue E2E"):
    page.goto(f"{live_server}/eventos/novo/")
    if page.url.endswith("/bloqueado/"):
        raise AssertionError(f"{etype}: já bloqueado ANTES do POST | cookies={page.context.cookies()}")
    page.select_option("#id_event_type", etype)
    page.select_option("#id_account", label=conta_label)
    for name, valor in campos.items():
        campo = page.locator(f"#id_{name}")
        if campo.evaluate("el => el.tagName") == "SELECT":
            campo.select_option(str(valor))
        else:
            campo.fill(str(valor))
    page.fill("#id_ptax_manual", PTAX["ptax_manual"])
    page.fill("#id_ptax_reason", PTAX["ptax_reason"])
    page.click("#event-form button[type=submit]")
    try:
        page.wait_for_url(f"{live_server}/", timeout=5000)
    except pw.TimeoutError:
        erros = page.locator(".errors").all_inner_texts()
        corpo = re.sub(r"\s+", " ", page.inner_text("body"))[:300]
        raise AssertionError(f"form de {etype} inválido: {erros} | URL: {page.url} | {corpo}")


def test_fluxo_completo_8_eventos(live_server, page, conta, vault_ready):
    _login(page, live_server)
    cadastrar_ativo(page, live_server, "AAPL")

    _evento(page, live_server, "APORTE", {"trade_date": "2026-01-05", "amount_usd": "10000"})
    _evento(page, live_server, "BUY", {"trade_date": "2026-01-10", "asset_ticker": "AAPL",
                                       "quantity": "100", "price_usd": "100", "fee_usd": "1"})
    _evento(page, live_server, "DIVIDEND", {"trade_date": "2026-03-20", "asset_ticker": "AAPL",
                                            "quantity": "100", "per_share_usd": "0.25",
                                            "tax_usd": "4.13",
                                            "foreign_tax_payment_date": "2026-03-20",
                                            "date_evidence_source": "BROKER_STATEMENT",
                                            "country_code": "US", "jurisdiction_level": "FEDERAL",
                                            "tax_type": "WITHHOLDING_INCOME_TAX"})
    _evento(page, live_server, "SELL", {"trade_date": "2026-06-10", "asset_ticker": "AAPL",
                                        "quantity": "40", "price_usd": "120", "fee_usd": "1"})
    _evento(page, live_server, "JUROS", {"trade_date": "2026-07-01", "amount_usd": "500"})
    _evento(page, live_server, "FEE", {"trade_date": "2026-07-15", "amount_usd": "5"})
    _evento(page, live_server, "TAX_WITHHELD", {"trade_date": "2026-07-20", "amount_usd": "10"})
    _evento(page, live_server, "WITHDRAWAL", {"trade_date": "2026-08-01", "amount_usd": "1000"})

    # Aba Eventos: 8 lançamentos (rótulos em português)
    page.goto(f"{live_server}/")
    conteudo = page.content()
    for rotulo in ["Aporte", "Retirada", "Compra", "Venda", "Dividendo",
                   "Juros/rendimento", "Taxa/corretagem", "Imposto retido"]:
        assert rotulo in conteudo, f"evento {rotulo} não listado"

    # Aba Posições: 60 AAPL, custo médio 100.01 USD
    page.goto(f"{live_server}/posicoes/")
    pos = re.sub(r"\s+", " ", page.inner_text("body"))
    assert "AAPL" in pos
    assert "60" in pos
    assert "100.01" in pos or "100,01" in pos

    # Aba Caixa: 10000 -10001 +4799 +20.87 +500 -5 -10 -1000 = 4303.87
    page.goto(f"{live_server}/caixa/")
    caixa = re.sub(r"\s+", " ", page.inner_text("body"))
    esperado = re.compile(r"4303[.,]87")
    assert esperado.search(caixa), f"saldo 4303.87 não encontrado em: {caixa[:500]}"


def test_excluir_evento_soft_delete(live_server, page, conta, vault_ready, regra_2026):
    _login(page, live_server)
    cadastrar_ativo(page, live_server, "AAPL")
    _evento(page, live_server, "BUY", {"trade_date": "2026-01-10", "asset_ticker": "AAPL",
                                       "quantity": "10", "price_usd": "100"})
    page.goto(f"{live_server}/posicoes/")
    assert "AAPL" in page.inner_text("body")

    # excluir: confirma o dialog de confirmação
    page.goto(f"{live_server}/")
    page.on("dialog", lambda d: d.accept())
    page.locator("form[action*='desativar'] button").first.click()
    page.wait_for_url(f"{live_server}/")

    corpo = page.inner_text("body")
    assert "Compra" not in corpo, "evento excluído ainda listado"
    page.goto(f"{live_server}/posicoes/")
    assert "AAPL" not in page.inner_text("body"), "posição contabilizou evento excluído"
