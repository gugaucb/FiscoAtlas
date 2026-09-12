#!/usr/bin/env python3
"""Cenário completo do manual + saldos documentais + fechamento do ano
(recaptura de 16b-apuracao-fechada.png com o botão Reabrir ano).
Base em docs/manual/capture_screenshots.py."""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8010"
IMG_DIR = Path(__file__).parent / "images"
SENHA = "TesteSenha2026!"
VIEWPORT = {"width": 1440, "height": 900}


def click_main_submit(page):
    btn = page.query_selector('main button[type="submit"]')
    if btn:
        btn.click()
        return
    buttons = page.query_selector_all('button[type="submit"]')
    (buttons[-1] if len(buttons) > 1 else buttons[0]).click()


def wait_and_check(page, label=""):
    page.wait_for_load_state("networkidle")
    time.sleep(0.5)
    if "/bloqueado/" in page.url:
        page.fill('#password', SENHA)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")
        return
    corpo = page.text_content("body") or ""
    if "errorlist" in corpo:
        print(f"    ⚠️ {label} erro no formulário")


def novo_evento(page, acct, tipo, data, **campos):
    page.goto(f"{BASE}/eventos/novo/")
    page.wait_for_load_state("networkidle")
    time.sleep(0.4)
    page.select_option('#id_event_type', tipo)
    time.sleep(0.3)
    if acct:
        page.select_option('#id_account', acct)
    page.fill('#id_trade_date', data)
    for sel, val in campos.items():
        page.fill(sel, val)
    click_main_submit(page)
    wait_and_check(page, tipo)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=VIEWPORT)
        page = context.new_page()
        page.on("dialog", lambda d: d.accept())

        # SETUP
        page.goto(f"{BASE}/bloqueado/")
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        if 'password2' in page.content():
            page.fill('#password', SENHA)
            page.fill('#password2', SENHA)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")
            time.sleep(1)
            print("Setup OK")

        # PERFIL
        page.goto(f"{BASE}/perfil/")
        page.wait_for_load_state("networkidle")
        page.fill('#id_name', "João da Silva")
        page.fill('#id_cpf', "000.000.000-00")
        page.select_option('#id_tax_residency_status', "BRAZIL_RESIDENT")
        click_main_submit(page)
        wait_and_check(page, "Perfil")

        # CONTAS
        for nome, broker, num in (("Broker A", "Interactive Brokers", "12345678"),
                                  ("Broker B", "Charles Schwab", "87654321")):
            page.goto(f"{BASE}/contas/")
            page.wait_for_load_state("networkidle")
            page.fill('#id_name', nome)
            page.fill('#id_broker_name', broker)
            page.fill('#id_account_number', num)
            page.select_option('#id_account_type', "CASH")
            click_main_submit(page)
            wait_and_check(page, nome)

        page.goto(f"{BASE}/eventos/novo/")
        page.wait_for_load_state("networkidle")
        a_val = b_val = None
        for opt in page.query_selector_all('#id_account option'):
            if "Broker A" in (opt.text_content() or ""):
                a_val = opt.get_attribute("value")
            if "Broker B" in (opt.text_content() or ""):
                b_val = opt.get_attribute("value")
        print(f"Contas A={a_val} B={b_val}")

        # ATIVOS
        for ticker, desc in (("AAPL", "Apple Inc"), ("LOSS", "Loss Corp")):
            page.goto(f"{BASE}/ativos/novo/")
            page.wait_for_load_state("networkidle")
            page.fill('#id_ticker', ticker)
            page.fill('#id_description', desc)
            page.select_option('#id_asset_type', "FOREIGN_EQUITY")
            page.fill('#id_country_code', "US")
            click_main_submit(page)
            wait_and_check(page, ticker)

        # EVENTOS
        novo_evento(page, a_val, "APORTE", "2026-01-10", **{'#id_amount_usd': "10000"})
        novo_evento(page, a_val, "BUY", "2026-01-15", **{
            '#id_asset_ticker': "AAPL", '#id_quantity': "100",
            '#id_price_usd': "50", '#id_fee_usd': "0"})
        novo_evento(page, a_val, "BUY", "2026-02-15", **{
            '#id_asset_ticker': "LOSS", '#id_quantity': "20",
            '#id_price_usd': "100", '#id_fee_usd': "0"})
        # Dividendo (bruto 200, retenção 60 → líquido 140 no caixa)
        page.goto(f"{BASE}/eventos/novo/")
        page.wait_for_load_state("networkidle")
        page.select_option('#id_event_type', "DIVIDEND")
        time.sleep(0.3)
        page.select_option('#id_account', a_val)
        page.fill('#id_trade_date', "2026-03-15")
        for sel, val in (('#id_asset_ticker', "AAPL"), ('#id_quantity', "100"),
                         ('#id_per_share_usd', "2.00"), ('#id_tax_usd', "60")):
            page.fill(sel, val)
        try:
            page.check('#id_confirm_same_day')
            page.select_option('#id_date_evidence_source', "BROKER_STATEMENT")
            page.select_option('#id_jurisdiction_level', "FEDERAL")
            page.select_option('#id_tax_type', "WITHHOLDING_INCOME_TAX")
        except Exception as e:
            print(f"    ⚠️ dividendo extras: {e}")
        click_main_submit(page)
        wait_and_check(page, "Dividendo")
        novo_evento(page, a_val, "SELL", "2026-06-15", **{
            '#id_asset_ticker': "AAPL", '#id_quantity': "50",
            '#id_price_usd': "70", '#id_fee_usd': "0"})
        novo_evento(page, a_val, "SELL", "2026-07-15", **{
            '#id_asset_ticker': "LOSS", '#id_quantity': "20",
            '#id_price_usd': "80", '#id_fee_usd': "0"})
        novo_evento(page, b_val, "APORTE", "2026-09-01", **{'#id_amount_usd': "1000"})

        # SALDOS DOCUMENTAIS 31/12/2026 (caixa do ledger: A 8.240 / B 1.000)
        def saldo(acct, cash, posicoes):
            page.goto(f"{BASE}/documentar-saldos/")
            page.wait_for_load_state("networkidle")
            page.select_option('#id_account', acct)
            page.fill('#id_reference_date', "2026-12-31")
            page.fill('#id_cash_usd', cash)
            if posicoes:
                page.fill('#id_positions_text', posicoes)
            page.check('#id_confirmed')
            click_main_submit(page)
            wait_and_check(page, "saldo")

        # Classificar recuperabilidade do imposto exterior (PK 1)
        page.goto(f"{BASE}/imposto-exterior/1/editar/")
        page.wait_for_load_state("networkidle")
        try:
            page.select_option('#id_recoverability_status', "NON_RECOVERABLE")
            page.fill('#id_reason', "Retenção definitiva na fonte (EUA)")
            # input type=date exige ISO; o template renderiza DD/MM/AAAA
            page.fill('#id_foreign_tax_payment_date', "2026-03-15")
            page.click('#save-payment')
            wait_and_check(page, "imposto exterior")
        except Exception as e:
            print(f"    ⚠️ recoverability: {e}")

        saldo(a_val, "8240.00", "AAPL, 50")
        saldo(b_val, "1000.00", None)
        print("Saldos documentais OK")

        # FECHAR ANO
        page.goto(f"{BASE}/apuracao/2026/")
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        fechar = page.query_selector('main form[action*="fechar"] button[type="submit"]')
        if fechar:
            fechar.click()
            page.wait_for_load_state("networkidle")
            time.sleep(2)
        else:
            print("⚠️ botão fechar não encontrado")
        page.goto(f"{BASE}/apuracao/2026/")
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        body = page.text_content("body") or ""
        ok = "Ano fechado" in body
        print("estado:", "FECHADO ✅" if ok else "ABERTO ❌")
        print("reabrir:", "botão Reabrir ✅" if "Reabrir ano" in body else "sem Reabrir ❌")
        i = body.find("Caixa de")
        if i >= 0:
            print("issue:", " ".join(body[i:i + 200].split()))
        if ok:
            page.screenshot(path=str(IMG_DIR / "16b-apuracao-fechada.png"), full_page=True)
            print("📸 16b-apuracao-fechada.png")
        browser.close()


if __name__ == "__main__":
    main()
