#!/usr/bin/env python3
"""Script Playwright para captura de screenshots e cenário de teste do FiscoAtlas.

Executa o fluxo completo:
1. Setup de senha
2. Cadastro do contribuinte
3. Criação de contas
4. Cadastro de ativos e eventos
5. Verificação de posições e caixa
6. Apuração anual e relatório DIRPF
7. Captura de screenshots de todas as telas
"""
import json
import re
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000"
IMG_DIR = Path(__file__).parent / "images"
IMG_DIR.mkdir(exist_ok=True)

SENHA = "TesteSenha2026!"
VIEWPORT = {"width": 1440, "height": 900}

collected_data = {}


def screenshot(page, name, full_page=False):
    path = IMG_DIR / name
    page.screenshot(path=str(path), full_page=full_page)
    print(f"  📸 {name}")


def click_main_submit(page):
    """Clica no botão submit PRINCIPAL do formulário (não o 'Bloquear' da nav).
    
    O template base tem um form 'Bloquear' com button[type=submit] na navbar.
    page.click('button[type=submit]') seleciona o primeiro, que é o Bloquear.
    Precisamos clicar no submit do form principal (main > form).
    """
    # Buscar submit buttons dentro de main (conteúdo principal)
    btn = page.query_selector('main button[type="submit"]')
    if btn:
        btn.click()
        return
    # Fallback: buscar o último submit button (geralmente o do form principal)
    buttons = page.query_selector_all('button[type="submit"]')
    if len(buttons) > 1:
        buttons[-1].click()
    elif buttons:
        buttons[0].click()


def safe_fill(page, selector, value, timeout=5000):
    try:
        page.fill(selector, value, timeout=timeout)
    except Exception:
        print(f"    ⚠️ Campo não encontrado: {selector}")


def safe_select(page, selector, value, timeout=5000):
    try:
        page.select_option(selector, value, timeout=timeout)
    except Exception:
        print(f"    ⚠️ Select não encontrado: {selector}")


def safe_check(page, selector, timeout=5000):
    try:
        page.check(selector, timeout=timeout)
    except Exception:
        print(f"    ⚠️ Checkbox não encontrado: {selector}")


def wait_and_check(page, label=""):
    page.wait_for_load_state("networkidle")
    time.sleep(0.5)
    # Verificar se foi redirecionado para /bloqueado/
    if "/bloqueado/" in page.url:
        print(f"    ⚠️ {label} VAULT LOCKED! Re-desbloqueando...")
        page.fill('#password', SENHA)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        return True
    errors = page.query_selector_all(".errorlist li, .errors")
    for e in errors:
        txt = e.text_content().strip()
        if txt:
            print(f"    ⚠️ {label} Erro: {txt}")
    msgs = page.query_selector_all(".messages li")
    for m in msgs:
        txt = m.text_content().strip()
        if txt:
            print(f"    ✅ {txt}")
    return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=150)
        context = browser.new_context(viewport=VIEWPORT)
        page = context.new_page()

        # ============================================================
        # FASE 1: SETUP / UNLOCK
        # ============================================================
        print("\n=== FASE 1: SETUP ===")
        page.goto(f"{BASE}/bloqueado/")
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        screenshot(page, "01-setup-senha.png")

        page_html = page.content()
        if 'password2' in page_html:
            print("  Modo: SETUP (banco novo)")
            page.fill('#password', SENHA)
            page.fill('#password2', SENHA)
            screenshot(page, "01b-setup-preenchido.png")
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")
            time.sleep(1)
            screenshot(page, "02-recovery-key.png")
            body_text = page.text_content("body")
            rk_match = re.search(r'([A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4})', body_text)
            collected_data["recovery_key"] = rk_match.group(1) if rk_match else "NÃO ENCONTRADA"
            print(f"  Recovery key: {collected_data['recovery_key']}")
        else:
            print("  Modo: UNLOCK (vault já configurado)")
            page.fill('#password', SENHA)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")
            time.sleep(1)
            collected_data["recovery_key"] = "(pré-existente)"
            print("  Desbloqueado")
            
            # Se a imagem 02-recovery-key.png ainda não existir, captura via /seguranca/
            if not (IMG_DIR / "02-recovery-key.png").exists():
                print("  Capturando tela de Recovery Key via /seguranca/...")
                page.goto(f"{BASE}/seguranca/")
                page.wait_for_load_state("networkidle")
                time.sleep(1)
                btn = page.query_selector('main form[action*="recovery/regenerar"] button') or page.query_selector('main button[type="submit"]')
                if btn:
                    btn.click()
                    page.wait_for_load_state("networkidle")
                    time.sleep(1)
                    screenshot(page, "02-recovery-key.png")

        # ============================================================
        # FASE 2: DASHBOARD
        # ============================================================
        print("\n=== FASE 2: DASHBOARD ===")
        page.goto(f"{BASE}/")
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        screenshot(page, "03-dashboard-vazio.png")
        nav = page.query_selector("nav")
        if nav:
            print("  Menu:")
            for link in nav.query_selector_all("a"):
                txt = link.text_content().strip()
                href = link.get_attribute("href") or ""
                if txt:
                    print(f"    {txt} → {href}")

        # ============================================================
        # FASE 3: PERFIL
        # ============================================================
        print("\n=== FASE 3: PERFIL ===")
        page.goto(f"{BASE}/perfil/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        screenshot(page, "04-perfil-vazio.png")
        page.fill('#id_name', "João da Silva")
        page.fill('#id_cpf', "000.000.000-00")
        page.select_option('#id_tax_residency_status', "BRAZIL_RESIDENT")
        screenshot(page, "04b-perfil-preenchido.png")
        click_main_submit(page)
        wait_and_check(page, "Perfil")
        screenshot(page, "04c-perfil-salvo.png")
        print("  Perfil cadastrado")

        # ============================================================
        # FASE 4: CONTAS
        # ============================================================
        print("\n=== FASE 4: CONTAS ===")
        page.goto(f"{BASE}/contas/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        screenshot(page, "05-contas-vazia.png")

        # Conta A
        page.fill('#id_name', "Broker A")
        page.fill('#id_broker_name', "Interactive Brokers")
        page.fill('#id_account_number', "12345678")
        page.select_option('#id_account_type', "CASH")
        screenshot(page, "05b-conta-a-preenchida.png")
        click_main_submit(page)
        wait_and_check(page, "Conta A")
        time.sleep(0.5)
        print("  Conta A criada")

        # Conta B
        page.goto(f"{BASE}/contas/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        page.fill('#id_name', "Broker B")
        page.fill('#id_broker_name', "Charles Schwab")
        page.fill('#id_account_number', "87654321")
        page.select_option('#id_account_type', "CASH")
        click_main_submit(page)
        wait_and_check(page, "Conta B")
        time.sleep(0.5)
        screenshot(page, "06-contas-lista.png")
        print("  Conta B criada")

        # Pegar IDs das contas para selecionar nos eventos
        page.goto(f"{BASE}/contas/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)

        # ============================================================
        # FASE 5: ATIVOS
        # ============================================================
        print("\n=== FASE 5: ATIVOS ===")
        page.goto(f"{BASE}/ativos/novo/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        screenshot(page, "07-ativo-form-vazio.png")
        page.fill('#id_ticker', "AAPL")
        page.fill('#id_description', "Apple Inc")
        page.select_option('#id_asset_type', "FOREIGN_EQUITY")
        page.fill('#id_country_code', "US")
        screenshot(page, "07b-ativo-aapl.png")
        click_main_submit(page)
        wait_and_check(page, "AAPL")
        print("  AAPL cadastrado")

        page.goto(f"{BASE}/ativos/novo/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        page.fill('#id_ticker', "LOSS")
        page.fill('#id_description', "Loss Corp")
        page.select_option('#id_asset_type', "FOREIGN_EQUITY")
        page.fill('#id_country_code', "US")
        click_main_submit(page)
        wait_and_check(page, "LOSS")
        screenshot(page, "07c-ativos-cadastrados.png")
        print("  LOSS cadastrado")

        # ============================================================
        # FASE 6: EVENTOS
        # ============================================================
        print("\n=== FASE 6: EVENTOS ===")

        # Função auxiliar para obter valores das opções de conta
        def get_account_values(page):
            page.goto(f"{BASE}/eventos/novo/")
            page.wait_for_load_state("networkidle")
            time.sleep(0.5)
            opts = page.query_selector_all('#id_account option')
            a_val, b_val = None, None
            for opt in opts:
                txt = opt.text_content()
                val = opt.get_attribute("value")
                if "Broker A" in txt: a_val = val
                if "Broker B" in txt: b_val = val
            return a_val, b_val

        acct_a, acct_b = get_account_values(page)
        print(f"  Conta A={acct_a}, Conta B={acct_b}")

        # --- Evento 1: Aporte USD 10.000 ---
        print("  [1] Aporte USD 10.000")
        page.goto(f"{BASE}/eventos/novo/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        screenshot(page, "08-evento-form-vazio.png")
        page.select_option('#id_event_type', "APORTE")
        time.sleep(0.3)
        if acct_a: page.select_option('#id_account', acct_a)
        page.fill('#id_trade_date', "2026-01-10")
        page.fill('#id_amount_usd', "10000")
        screenshot(page, "08b-aporte-preenchido.png")
        click_main_submit(page)
        wait_and_check(page, "Aporte")

        # --- Evento 2: Compra AAPL ---
        print("  [2] Compra AAPL 100×50")
        page.goto(f"{BASE}/eventos/novo/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        page.select_option('#id_event_type', "BUY")
        if acct_a: page.select_option('#id_account', acct_a)
        safe_fill(page, '#id_asset_ticker', "AAPL")
        page.fill('#id_trade_date', "2026-01-15")
        safe_fill(page, '#id_quantity', "100")
        safe_fill(page, '#id_price_usd', "50")
        safe_fill(page, '#id_fee_usd', "0")
        screenshot(page, "09-compra-aapl.png")
        click_main_submit(page)
        wait_and_check(page, "Compra AAPL")

        # --- Evento 3: Compra LOSS ---
        print("  [3] Compra LOSS 20×100")
        page.goto(f"{BASE}/eventos/novo/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        page.select_option('#id_event_type', "BUY")
        if acct_a: page.select_option('#id_account', acct_a)
        safe_fill(page, '#id_asset_ticker', "LOSS")
        page.fill('#id_trade_date', "2026-02-15")
        safe_fill(page, '#id_quantity', "20")
        safe_fill(page, '#id_price_usd', "100")
        safe_fill(page, '#id_fee_usd', "0")
        click_main_submit(page)
        wait_and_check(page, "Compra LOSS")

        # --- Evento 4: Dividendo AAPL ---
        print("  [4] Dividendo AAPL (bruto=200, IR=60)")
        page.goto(f"{BASE}/eventos/novo/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        page.select_option('#id_event_type', "DIVIDEND")
        time.sleep(0.3)
        if acct_a: page.select_option('#id_account', acct_a)
        safe_fill(page, '#id_asset_ticker', "AAPL")
        page.fill('#id_trade_date', "2026-03-15")
        safe_fill(page, '#id_quantity', "100")
        safe_fill(page, '#id_per_share_usd', "2.00")
        safe_fill(page, '#id_tax_usd', "60")
        safe_check(page, '#id_confirm_same_day')
        safe_select(page, '#id_date_evidence_source', "BROKER_STATEMENT")
        safe_select(page, '#id_jurisdiction_level', "FEDERAL")
        safe_fill(page, '#id_country_code', "US")
        safe_select(page, '#id_tax_type', "WITHHOLDING_INCOME_TAX")
        screenshot(page, "10-dividendo-preenchido.png", full_page=True)
        click_main_submit(page)
        wait_and_check(page, "Dividendo")

        # --- Evento 5: Venda AAPL (lucro) ---
        print("  [5] Venda AAPL 50×70 (lucro)")
        page.goto(f"{BASE}/eventos/novo/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        page.select_option('#id_event_type', "SELL")
        if acct_a: page.select_option('#id_account', acct_a)
        safe_fill(page, '#id_asset_ticker', "AAPL")
        page.fill('#id_trade_date', "2026-06-15")
        safe_fill(page, '#id_quantity', "50")
        safe_fill(page, '#id_price_usd', "70")
        safe_fill(page, '#id_fee_usd', "0")
        screenshot(page, "11-venda-aapl.png")
        click_main_submit(page)
        wait_and_check(page, "Venda AAPL")

        # --- Evento 6: Venda LOSS (prejuízo) ---
        print("  [6] Venda LOSS 20×80 (prejuízo)")
        page.goto(f"{BASE}/eventos/novo/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        page.select_option('#id_event_type', "SELL")
        if acct_a: page.select_option('#id_account', acct_a)
        safe_fill(page, '#id_asset_ticker', "LOSS")
        page.fill('#id_trade_date', "2026-07-15")
        safe_fill(page, '#id_quantity', "20")
        safe_fill(page, '#id_price_usd', "80")
        safe_fill(page, '#id_fee_usd', "0")
        click_main_submit(page)
        wait_and_check(page, "Venda LOSS")

        # --- Evento 7: Aporte Conta B ---
        print("  [7] Aporte USD 1.000 (Conta B)")
        page.goto(f"{BASE}/eventos/novo/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        page.select_option('#id_event_type', "APORTE")
        if acct_b: page.select_option('#id_account', acct_b)
        page.fill('#id_trade_date', "2026-09-01")
        page.fill('#id_amount_usd', "1000")
        click_main_submit(page)
        wait_and_check(page, "Aporte B")

        # ============================================================
        # FASE 7: LISTA DE EVENTOS
        # ============================================================
        print("\n=== FASE 7: LISTA DE EVENTOS ===")
        page.goto(f"{BASE}/")
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        screenshot(page, "13-eventos-lista.png", full_page=True)
        rows = page.query_selector_all("table tbody tr")
        print(f"  Eventos: {len(rows)}")
        for row in rows[:10]:
            print(f"    {row.text_content().strip()[:120]}")

        # ============================================================
        # FASE 8: POSIÇÕES
        # ============================================================
        print("\n=== FASE 8: POSIÇÕES ===")
        page.goto(f"{BASE}/posicoes/")
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        screenshot(page, "14-posicoes.png")
        print(f"  {page.text_content('body')[:300]}")

        # ============================================================
        # FASE 9: CAIXA
        # ============================================================
        print("\n=== FASE 9: CAIXA ===")
        page.goto(f"{BASE}/caixa/")
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        screenshot(page, "15-caixa.png", full_page=True)
        print(f"  {page.text_content('body')[:300]}")

        # ============================================================
        # FASE 10: APURAÇÃO 2026
        # ============================================================
        print("\n=== FASE 10: APURAÇÃO ===")
        page.goto(f"{BASE}/apuracao/2026/")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        screenshot(page, "16-apuracao-2026.png", full_page=True)
        apuracao = page.text_content("body")
        print(f"  {apuracao[:600]}")

        # ============================================================
        # FASE 11: RELATÓRIO 2026
        # ============================================================
        print("\n=== FASE 11: RELATÓRIO ===")
        page.goto(f"{BASE}/relatorio/2026/")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        screenshot(page, "17-relatorio-2026.png", full_page=True)
        report = page.text_content("body")
        print(f"  {report[:600]}")

        # PTAX de fechamento manual se necessário
        if page.query_selector('#id_rate'):
            print("  ⚠️ PTAX de fechamento necessária")
            page.fill('#id_rate', "5.8468")
            safe_fill(page, '#id_motivo', "Data futura (31/12/2026) - cotação fictícia de teste")
            screenshot(page, "17b-ptax-fechamento.png")
            click_main_submit(page)
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            screenshot(page, "17c-relatorio-com-ptax.png", full_page=True)
            report = page.text_content("body")
            print(f"  {report[:600]}")

        # ============================================================
        # FASE 12: FECHAR ANO
        # ============================================================
        print("\n=== FASE 12: FECHAR ANO ===")
        page.goto(f"{BASE}/apuracao/2026/")
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        fechar = page.query_selector('main form[action*="fechar"] button[type="submit"]')
        if fechar:
            fechar.click()
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            screenshot(page, "16b-apuracao-fechada.png", full_page=True)
            print(f"  {page.text_content('body')[:300]}")
        else:
            # Tentar outro seletor
            btns = page.query_selector_all('main button')
            for btn in btns:
                if 'Fechar' in (btn.text_content() or ''):
                    btn.click()
                    page.wait_for_load_state("networkidle")
                    time.sleep(2)
                    screenshot(page, "16b-apuracao-fechada.png", full_page=True)
                    break
            else:
                print("  ⚠️ Botão de fechar não encontrado")
                screenshot(page, "16b-apuracao-sem-fechar.png", full_page=True)

        # ============================================================
        # FASE 13: RELATÓRIO FINAL
        # ============================================================
        print("\n=== FASE 13: RELATÓRIO FINAL ===")
        page.goto(f"{BASE}/relatorio/2026/")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        screenshot(page, "21-relatorio-final.png", full_page=True)
        final = page.text_content("body")
        collected_data["relatorio_final"] = final
        print(f"  {final[:600]}")

        # ============================================================
        # FASE 14: SEGURANÇA
        # ============================================================
        print("\n=== FASE 14: SEGURANÇA ===")
        page.goto(f"{BASE}/seguranca/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        screenshot(page, "18-seguranca.png")

        # ============================================================
        # FASE 15: DOCUMENTOS
        # ============================================================
        print("\n=== FASE 15: DOCUMENTOS ===")
        page.goto(f"{BASE}/documentos/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        screenshot(page, "19-documentos.png")

        # ============================================================
        # FASE 16: POSIÇÃO DE ABERTURA
        # ============================================================
        print("\n=== FASE 16: POSIÇÃO DE ABERTURA ===")
        page.goto(f"{BASE}/posicao-abertura/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        screenshot(page, "20-posicao-abertura.png")

        # ============================================================
        # FASE 17: LOCK/UNLOCK
        # ============================================================
        print("\n=== FASE 17: LOCK/UNLOCK ===")
        lock_btn = page.query_selector('form[action*="bloquear"] button[type="submit"]')
        if lock_btn:
            lock_btn.click()
            page.wait_for_load_state("networkidle")
            time.sleep(1)
        screenshot(page, "22-tela-bloqueio.png")
        if page.query_selector('#password'):
            page.fill('#password', SENHA)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")
            time.sleep(1)
            print("  Lock/Unlock OK")

        # ============================================================
        # FASE 18: PERSISTÊNCIA
        # ============================================================
        print("\n=== FASE 18: PERSISTÊNCIA ===")
        page.goto(f"{BASE}/perfil/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        nome = page.input_value('#id_name') if page.query_selector('#id_name') else ""
        print(f"  Perfil nome: '{nome}' {'✅' if nome == 'João da Silva' else '❌'}")

        page.goto(f"{BASE}/contas/")
        page.wait_for_load_state("networkidle")
        body = page.text_content("body")
        print(f"  Contas: {'✅' if 'Broker A' in body and 'Broker B' in body else '❌'}")

        page.goto(f"{BASE}/")
        page.wait_for_load_state("networkidle")
        body = page.text_content("body")
        print(f"  Eventos: {'✅' if 'AAPL' in body else '❌'}")

        # ============================================================
        # FASE 19: EDIÇÃO DE CONTA
        # ============================================================
        print("\n=== FASE 19: EDIÇÃO ===")
        page.goto(f"{BASE}/contas/")
        page.wait_for_load_state("networkidle")
        edit_link = page.query_selector('a:has-text("editar")')
        if edit_link:
            edit_link.click()
            page.wait_for_load_state("networkidle")
            time.sleep(0.5)
            screenshot(page, "23-edicao-conta.png")
            print("  Edição de conta OK")

        # ============================================================
        # FINALIZAÇÃO
        # ============================================================
        print("\n" + "=" * 50)
        print("=== SCREENSHOTS CAPTURADOS ===")
        print("=" * 50)
        imgs = sorted(IMG_DIR.glob("*.png"))
        for img in imgs:
            print(f"  ✅ {img.name} ({img.stat().st_size / 1024:.0f} KB)")
        print(f"\nTotal: {len(imgs)} screenshots")

        data_file = IMG_DIR.parent / "collected_data.json"
        with open(data_file, "w") as f:
            json.dump(collected_data, f, indent=2, default=str)
        print(f"Dados salvos em: {data_file}")

        browser.close()
        print("\n✅ Script concluído com sucesso!")


if __name__ == "__main__":
    main()
