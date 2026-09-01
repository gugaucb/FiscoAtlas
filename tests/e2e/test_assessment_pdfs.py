"""E2E browser: apuração 2026 + os dois PDFs, comparando valores esperados.

Cenário (PTAX manual 5,40 em todos os eventos):
- SELL 40 AAPL: sale 4799×5,4=25.914,60; custo 40×540,054=21.602,16 → ganho 4.312,44
- DIVIDEND: bruto 25×5,4=135,00; withholding 4,13×5,4=22,30; crédito 15% → 20,25
- JUROS: 500×5,4=2.700,00
- renda=7.147,44; sem prejuízo; imposto=1.072,12; devido=1.051,87
"""
import io
import re

import pytest

pw = pytest.importorskip("playwright.sync_api")

from tests.e2e.conftest import login, novo_evento, seed_8_eventos

pypdf = pytest.importorskip("pypdf")

YEARS = "2026"


def _num(soup_text, valor):
    """Procura o valor (ex. '7147.44') em qualquer formatação pt-BR/en-US."""
    inteiro, dec = str(valor).split(".")
    return re.compile(rf"{inteiro}[.,]{dec}\b") .search(soup_text)


@pytest.fixture
def fluxo(live_server, page, conta, vault_ready, regra_2026, db):
    login(page, live_server)
    seed_8_eventos(page, live_server)
    return live_server, page


def informar_ptax_fechamento(page, live_server):
    """31/12/2026 é futuro: registra a PTAX pelo form inline do relatório."""
    page.goto(f"{live_server}/relatorio/{YEARS}/")
    assert "PTAX de fechamento" in page.inner_text("body")
    page.fill("#id_rate", "5.4000")
    page.fill("#id_motivo", "E2E: data futura")
    page.click("form[action*='ptax-fechamento'] button[type=submit]")
    page.wait_for_url(f"{live_server}/relatorio/{YEARS}/")
    corpo = page.inner_text("body")
    assert "PTAX de fechamento" not in corpo, "form não sumiu após salvar"


def test_apuracao_mostra_valores_esperados(fluxo):
    live_server, page = fluxo
    page.goto(f"{live_server}/apuracao/{YEARS}/")
    corpo = re.sub(r"\s+", " ", page.inner_text("body"))

    assert _num(corpo, "7147.44"), f"renda 7.147,44 ausente: {corpo[:400]}"
    assert _num(corpo, "4312.44"), "ganho 4.312,44 ausente"
    assert _num(corpo, "1072.12"), "imposto 1.072,12 ausente"
    assert _num(corpo, "20.25"), "crédito withholding 20,25 ausente"
    assert _num(corpo, "1051.87"), "imposto devido 1.051,87 ausente"


def test_pdf_relatorio_dirpf(fluxo, tmp_path):
    live_server, page = fluxo
    informar_ptax_fechamento(page, live_server)
    with page.expect_download() as dl:
        try:
            page.goto(f"{live_server}/relatorio/{YEARS}/pdf")
        except pw.Error:
            pass  # navegação abortada: virou download
    download = dl.value
    destino = tmp_path / "relatorio.pdf"
    download.save_as(destino)

    texto = "\n".join(p.extract_text() for p in pypdf.PdfReader(destino).pages)
    assert re.search(r"7\.?147[,.]44", texto), "renda ausente no PDF do relatório"
    assert re.search(r"4\.?312[,.]44", texto), "ganho ausente no PDF do relatório"
    assert re.search(r"20[,.]25", texto), "crédito ausente no PDF do relatório"
    assert "AAPL" in texto


def test_pdf_memoria_calculo(fluxo, tmp_path):
    live_server, page = fluxo
    with page.expect_download() as dl:
        try:
            page.goto(f"{live_server}/relatorio/{YEARS}/memoria-pdf")
        except pw.Error:
            pass  # navegação abortada: virou download
    download = dl.value
    destino = tmp_path / "memoria.pdf"
    download.save_as(destino)

    # memória é linha-a-linha por ativo (BUY/SELL/DIVIDEND), sem totais de renda
    texto = "\n".join(p.extract_text() for p in pypdf.PdfReader(destino).pages)
    assert re.search(r"4\.?312[,.]44", texto), "ganho da venda ausente na memória"
    assert re.search(r"21\.?602[,.]16", texto), "custo baixado ausente na memória"
    assert re.search(r"135[,.]00", texto), "dividendo bruto BRL ausente na memória"
    assert re.search(r"5[,.]4000", texto), "PTAX congelada ausente na memória"
    assert "AAPL" in texto
