"""Ticket 01 (e2e-browser-regressao) — cenário rico como usuário final.

Cria via UI: perfil, 2 contas (1 remunerada), 7 ativos (5 stocks + 2 ETFs),
20 eventos do ano 2026 + transferência de custódia 50 AAPL A→B via serviço
(sem form web). Verifica Posições e Caixa com valores esperados explícitos.

PTAX manual fixa 5.0000 em todos os eventos → contas em BRL determinísticos.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

pw = pytest.importorskip("playwright.sync_api")

from tests.e2e.conftest import login, seed_cenario_rico

RATE = Decimal("5.00000000")


def _num(txt):
    """Converte número localizado pt-br em Decimal ('30.000,50' → 30000.50)."""
    t = txt.strip().replace("USD", "").strip()
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    return Decimal(t)


# Posições finais por (ticker, quantidade, custo médio USD, custo total BRL).
# AAPL: 100@50 + 100@70 → média 60; venda de 100 e transferência de 50 →
# conta A fica com 50 e conta B com 50 (custo médio preservado na custódia).
# KO split 1:2 (100→200, média 30→15) e MSFT reverse 2:1 (30→15, média
# 100→200) — custo total BRL preservado, só o unitário se ajusta.
EXPECTED_ROWS = [
    ("AAPL", Decimal("50"), Decimal("60"), Decimal("15000")),
    ("AAPL", Decimal("50"), Decimal("60"), Decimal("15000")),
    ("VOO", Decimal("50"), Decimal("80"), Decimal("20000")),
    ("MSFT", Decimal("15"), Decimal("200"), Decimal("15000")),
    ("TSLA", Decimal("20"), Decimal("80"), Decimal("8000")),
    ("KO", Decimal("200"), Decimal("15"), Decimal("15000")),
    ("NVDA", Decimal("20"), Decimal("50"), Decimal("5000")),
]

# Caixa: 40000 − 29200 (compras) + 13100 (vendas) + 192.50 (dividendos
# LÍQUIDOS: 200−30 e 25−2.50) + 100 (juros) − 5 (taxa) − 1000 (retirada)
CAIXA_A = Decimal("23187.50")
CAIXA_B = Decimal("5000.00")


def _ler_saldo_caixa(page, conta_nome):
    p = page.locator("h2", has_text=conta_nome).locator(
        "xpath=following-sibling::p[1]")
    texto = p.inner_text()
    return _num(texto.split("USD")[1])


def test_cenario_rico_posicoes_e_caixa(live_server, page, transactional_db, vault_ready):
    login(page, live_server)
    conta_a, conta_b = seed_cenario_rico(page, live_server)

    # Transferência de custódia: 50 AAPL A→B (camada de serviço, par IN/OUT)
    from ledger.models import Asset, BrokerAccount
    from ledger.service import BrokerTransferService
    with mock.patch("ledger.service.BrokerTransferService._ptax_rate",
                    return_value=RATE):
        BrokerTransferService().record(
            out_account=BrokerAccount.objects.get(name=conta_a),
            in_account=BrokerAccount.objects.get(name=conta_b),
            trade_date=date(2026, 9, 15),
            asset=Asset.objects.get(ticker="AAPL"), quantity=Decimal(50))

    # Posições: 7 linhas (conta A × 6 ativos + conta B × AAPL)
    page.goto(f"{live_server}/posicoes/")
    page.wait_for_load_state("networkidle")
    rows = []
    for tr in page.locator("table tbody tr").all():
        cells = tr.locator("td").all_inner_texts()
        if len(cells) < 5:
            continue  # linha vazia (colspan)
        rows.append((cells[0].strip(), _num(cells[2]), _num(cells[3]), _num(cells[4])))
    assert sorted(rows) == sorted(EXPECTED_ROWS), \
        f"posições divergentes: obtido={sorted(rows)}"

    # Caixa: saldos e badge de conta remunerada
    page.goto(f"{live_server}/caixa/")
    page.wait_for_load_state("networkidle")
    assert _ler_saldo_caixa(page, conta_a) == CAIXA_A
    assert _ler_saldo_caixa(page, conta_b) == CAIXA_B
    p_a = page.locator("h2", has_text=conta_a).locator(
        "xpath=following-sibling::p[2]")
    assert "conta remunerada" in p_a.inner_text()
    p_b = page.locator("h2", has_text=conta_b).locator(
        "xpath=following-sibling::p[2]")
    assert "não remunerado" in p_b.inner_text()