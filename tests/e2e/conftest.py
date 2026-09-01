import os

import pytest

# Playwright roda o teste em contexto async; os fixtures usam ORM sync
# (mesmo processo do LiveServer, então é seguro aqui).
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")

PASSWORD = "test-password-123"


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
        page.fill(f"#id_{name}", str(valor))
    page.fill("#id_ptax_manual", PTAX["ptax_manual"])
    page.fill("#id_ptax_reason", PTAX["ptax_reason"])
    page.click("#event-form button[type=submit]")
    try:
        page.wait_for_url(f"{live_server}/", timeout=5000)
    except Exception:
        erros = page.locator(".errors").all_inner_texts()
        corpo = _re.sub(r"\s+", " ", page.inner_text("body"))[:300]
        raise AssertionError(f"form de {etype} inválido: {erros} | URL: {page.url} | {corpo}")


def seed_8_eventos(page, live_server):
    novo_evento(page, live_server, "APORTE", {"trade_date": "2026-01-05", "amount_usd": "10000"})
    novo_evento(page, live_server, "BUY", {"trade_date": "2026-01-10", "asset_ticker": "AAPL",
                                           "quantity": "100", "price_usd": "100", "fee_usd": "1"})
    novo_evento(page, live_server, "DIVIDEND", {"trade_date": "2026-03-20", "asset_ticker": "AAPL",
                                                "quantity": "100", "per_share_usd": "0.25",
                                                "tax_usd": "4.13"})
    novo_evento(page, live_server, "SELL", {"trade_date": "2026-06-10", "asset_ticker": "AAPL",
                                            "quantity": "40", "price_usd": "120", "fee_usd": "1"})
    novo_evento(page, live_server, "JUROS", {"trade_date": "2026-07-01", "amount_usd": "500"})
    novo_evento(page, live_server, "FEE", {"trade_date": "2026-07-15", "amount_usd": "5"})
    novo_evento(page, live_server, "TAX_WITHHELD", {"trade_date": "2026-07-20", "amount_usd": "10"})
    novo_evento(page, live_server, "WITHDRAWAL", {"trade_date": "2026-08-01", "amount_usd": "1000"})
