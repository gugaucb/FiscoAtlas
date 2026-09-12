import os

import pytest

# Playwright roda o teste em contexto async; os fixtures usam ORM sync
# (mesmo processo do LiveServer, então é seguro aqui).
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")

PASSWORD = "test-password-123"

pw = pytest.importorskip("playwright.sync_api")


@pytest.fixture
def vault_ready(db):
    from security.vault import VaultService

    svc = VaultService()
    if not svc.is_configured():
        svc.setup(PASSWORD)


import re as _re

PTAX = {"ptax_manual": "5.4000", "ptax_reason": "E2E: API fora"}


@pytest.fixture
def conta(db):
    from ledger.models import BrokerAccount

    return BrokerAccount.objects.create(
        broker_name="Avenue", account_number="E2E", country_code="US",
        is_interest_bearing=True, name="Avenue E2E",
    )


@pytest.fixture
def regra_2026(db):
    """TaxRule 2026 confirmada (mesma regra da Lei 14.754/2023)."""
    from datetime import date

    from fiscal.models import TaxRule

    TaxRule.objects.get_or_create(
        tax_year=2026,
        rule_version="e2e-v1",
        defaults={
            "brackets": [{"limit_brl": None, "rate": "0.15"}],
            "confirmed": True,
            "effective_from": date(2026, 1, 1),
        },
    )


def login(page, live_server):
    page.goto(f"{live_server}/bloqueado/")
    page.fill("#password", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_url(f"{live_server}/")


def novo_evento(page, live_server, etype, campos, conta_label="Avenue E2E"):
    page.goto(f"{live_server}/eventos/novo/")
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
    except Exception:
        erros = page.locator(".errors").all_inner_texts()
        corpo = _re.sub(r"\s+", " ", page.inner_text("body"))[:300]
        raise AssertionError(f"form de {etype} inválido: {erros} | URL: {page.url} | {corpo}")


def criar_perfil(page, live_server):
    """Perfil do contribuinte via UI (residência BRAZIL_RESIDENT)."""
    page.goto(f"{live_server}/perfil/")
    page.fill("#id_name", "João da Silva E2E")
    page.fill("#id_cpf", "000.000.000-00")
    page.select_option("#id_tax_residency_status", "BRAZIL_RESIDENT")
    page.click("form[method=post]:not([action]) button[type=submit]")
    page.wait_for_load_state("networkidle")


def criar_conta(page, live_server, nome, remunerada=False):
    """Conta de corretora via UI; retorna o label usado nos selects."""
    page.goto(f"{live_server}/contas/")
    page.fill("#id_name", nome)
    page.fill("#id_broker_name", f"Corretora {nome}")
    page.fill("#id_account_number", f"ACCT-{nome}")
    page.select_option("#id_account_type", "CASH")
    if remunerada:
        page.check("#id_is_interest_bearing")
    page.click("form[method=post]:not([action]) button[type=submit]")
    page.wait_for_load_state("networkidle")
    return nome


def seed_cenario_rico(page, live_server):
    """Cenário canônico do ticket 01 (regressão browser): perfil, 2 contas,
    7 ativos (5 stocks + 2 ETFs) e ano-calendário 2026 completo via UI.
    PTAX manual fixa 5.0000 → valores esperados determinísticos.
    Retorna dict com labels das contas."""
    PTAX_FIXO = {"ptax_manual": "5.0000", "ptax_reason": "E2E: cotação fixa"}
    criar_perfil(page, live_server)
    conta_a = criar_conta(page, live_server, "E2E Alpha", remunerada=True)
    conta_b = criar_conta(page, live_server, "E2E Beta")

    # 5 stocks + 2 ETFs
    ativos = [("AAPL", "FOREIGN_EQUITY"), ("MSFT", "FOREIGN_EQUITY"),
              ("KO", "FOREIGN_EQUITY"), ("TSLA", "FOREIGN_EQUITY"),
              ("NVDA", "FOREIGN_EQUITY"), ("VOO", "FOREIGN_ETF"),
              ("VTI", "FOREIGN_ETF")]
    for ticker, tipo in ativos:
        cadastrar_ativo(page, live_server, ticker, tipo)

    def ev2(etype, data, campos, conta_label):
        page.goto(f"{live_server}/eventos/novo/")
        page.select_option("#id_event_type", etype)
        page.select_option("#id_account", label=conta_label)
        campos = {"trade_date": data, **campos}
        for name, valor in campos.items():
            campo = page.locator(f"#id_{name}")
            if campo.evaluate("el => el.tagName") == "SELECT":
                campo.select_option(str(valor))
            elif campo.evaluate("el => el.type") == "checkbox":
                if valor:
                    campo.check()
            else:
                campo.fill(str(valor))
        page.fill("#id_ptax_manual", PTAX_FIXO["ptax_manual"])
        page.fill("#id_ptax_reason", PTAX_FIXO["ptax_reason"])
        page.click("#event-form button[type=submit]")
        try:
            page.wait_for_url(f"{live_server}/", timeout=5000)
        except pw.TimeoutError:
            erros = page.locator(".errors").all_inner_texts()
            corpo = _re.sub(r"\s+", " ", page.inner_text("body"))[:300]
            raise AssertionError(
                f"form de {etype} inválido: {erros} | URL: {page.url} | {corpo}")

    ev2("APORTE", "2026-01-05", {"amount_usd": "40000"}, conta_a)
    ev2("APORTE", "2026-01-06", {"amount_usd": "5000"}, conta_b)
    ev2("BUY", "2026-01-10", {"asset_ticker": "AAPL", "quantity": "100",
                              "price_usd": "50", "fee_usd": "0"}, conta_a)
    ev2("BUY", "2026-02-10", {"asset_ticker": "AAPL", "quantity": "100",
                              "price_usd": "70", "fee_usd": "0"}, conta_a)
    ev2("BUY", "2026-02-11", {"asset_ticker": "VOO", "quantity": "50",
                              "price_usd": "80", "fee_usd": "0"}, conta_a)
    ev2("BUY", "2026-03-05", {"asset_ticker": "MSFT", "quantity": "30",
                              "price_usd": "100", "fee_usd": "0"}, conta_a)
    ev2("BUY", "2026-03-10", {"asset_ticker": "TSLA", "quantity": "40",
                              "price_usd": "80", "fee_usd": "0"}, conta_a)
    ev2("BUY", "2026-04-01", {"asset_ticker": "KO", "quantity": "100",
                              "price_usd": "30", "fee_usd": "0"}, conta_a)
    ev2("BUY", "2026-04-02", {"asset_ticker": "NVDA", "quantity": "20",
                              "price_usd": "50", "fee_usd": "0"}, conta_a)
    ev2("BUY", "2026-04-03", {"asset_ticker": "VTI", "quantity": "60",
                              "price_usd": "50", "fee_usd": "0"}, conta_a)
    ev2("DIVIDEND", "2026-05-01", {"asset_ticker": "AAPL", "quantity": "200",
                                   "per_share_usd": "1.00", "tax_usd": "30",
                                   "foreign_tax_payment_date": "2026-05-01",
                                   "date_evidence_source": "BROKER_STATEMENT",
                                   "country_code": "US",
                                   "jurisdiction_level": "FEDERAL",
                                   "tax_type": "WITHHOLDING_INCOME_TAX",
                                   "recoverability_status": "NON_RECOVERABLE"}, conta_a)
    ev2("DIVIDEND", "2026-05-02", {"asset_ticker": "VOO", "quantity": "50",
                                   "per_share_usd": "0.50", "tax_usd": "2.50",
                                   "foreign_tax_payment_date": "2026-05-02",
                                   "date_evidence_source": "BROKER_STATEMENT",
                                   "country_code": "US",
                                   "jurisdiction_level": "FEDERAL",
                                   "tax_type": "WITHHOLDING_INCOME_TAX",
                                   "recoverability_status": "NON_RECOVERABLE"}, conta_a)
    ev2("SELL", "2026-06-01", {"asset_ticker": "AAPL", "quantity": "100",
                               "price_usd": "90", "fee_usd": "0"}, conta_a)
    ev2("SELL", "2026-07-01", {"asset_ticker": "TSLA", "quantity": "20",
                               "price_usd": "70", "fee_usd": "0"}, conta_a)
    ev2("SELL", "2026-07-02", {"asset_ticker": "VTI", "quantity": "60",
                               "price_usd": "45", "fee_usd": "0"}, conta_a)
    ev2("JUROS", "2026-08-01", {"amount_usd": "100"}, conta_a)
    ev2("FEE", "2026-08-15", {"amount_usd": "5"}, conta_a)
    ev2("WITHDRAWAL", "2026-09-01", {"amount_usd": "1000"}, conta_a)
    ev2("STOCK_SPLIT", "2026-10-01", {"asset_ticker": "KO",
                                      "split_ratio_from": "1",
                                      "split_ratio_to": "2"}, conta_a)
    ev2("REVERSE_SPLIT", "2026-10-15", {"asset_ticker": "MSFT",
                                        "split_ratio_from": "2",
                                        "split_ratio_to": "1"}, conta_a)
    return conta_a, conta_b


def cadastrar_ativo(page, live_server, ticker="AAPL", asset_type="FOREIGN_EQUITY"):
    """Cadastro explícito de ativo (ticket 01): sem auto-criação no formulário de eventos."""
    page.goto(f"{live_server}/ativos/novo/")
    page.fill("#id_ticker", ticker)
    page.fill("#id_description", f"Descrição {ticker}")
    page.select_option("#id_asset_type", asset_type)
    page.click("#save-asset")
    page.wait_for_url(f"{live_server}/eventos/novo/", timeout=5000)


def seed_8_eventos(page, live_server):
    cadastrar_ativo(page, live_server, "AAPL")
    novo_evento(page, live_server, "APORTE", {"trade_date": "2026-01-05", "amount_usd": "10000"})
    novo_evento(page, live_server, "BUY", {"trade_date": "2026-01-10", "asset_ticker": "AAPL",
                                           "quantity": "100", "price_usd": "100", "fee_usd": "1"})
    novo_evento(page, live_server, "DIVIDEND", {"trade_date": "2026-03-20", "asset_ticker": "AAPL",
                                                "quantity": "100", "per_share_usd": "0.25",
                                                "tax_usd": "4.13",
                                                "foreign_tax_payment_date": "2026-03-20",
                                                "date_evidence_source": "BROKER_STATEMENT",
                                                "country_code": "US", "jurisdiction_level": "FEDERAL",
                                                "tax_type": "WITHHOLDING_INCOME_TAX",
                                                "recoverability_status": "NON_RECOVERABLE"})
    novo_evento(page, live_server, "SELL", {"trade_date": "2026-06-10", "asset_ticker": "AAPL",
                                            "quantity": "40", "price_usd": "120", "fee_usd": "1"})
    novo_evento(page, live_server, "JUROS", {"trade_date": "2026-07-01", "amount_usd": "500"})
    novo_evento(page, live_server, "FEE", {"trade_date": "2026-07-15", "amount_usd": "5"})
    novo_evento(page, live_server, "TAX_WITHHELD", {"trade_date": "2026-07-20", "amount_usd": "10"})
    novo_evento(page, live_server, "WITHDRAWAL", {"trade_date": "2026-08-01", "amount_usd": "1000"})
