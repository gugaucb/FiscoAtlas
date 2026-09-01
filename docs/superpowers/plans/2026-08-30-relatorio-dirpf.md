# Relatório DIRPF (Plano 4/4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Relatório final para transcrever na DIRPF: posições de bens e direitos em 31/12 (Avenue, custo em USD e BRL pela PTAX do último dia útil do ano), saldo de caixa em 31/12, rendimentos e ganhos do ano (reutiliza `TaxEngine`), e download em PDF.

**Architecture:** App `ledger` (posição/caixa) ganha parâmetro `until`; novo app-level serviço `fiscal/report.py` (`ReportService` monta estrutura do relatório) e `fiscal/pdf.py` (render com reportlab). Tela HTML de conferência + rota de download do PDF.

**Tech Stack:** Django 5, reportlab (PDF puro Python, sem deps de sistema), pytest-django, venv local.

**Legislação:** avaliação de bens no exterior em BRL pela PTAX de compra (ou 31/12 para posição); bens declarados por custo de aquisição em BRL (código 70/71 da ficha Bens e Direitos — a confirmar com contador). PTAX de 31/12 = último dia útil (o `PtaxService` já recua dias sem cotação).

**Spec:** `docs/adr/0003-regras-lei-14754-2023.md`, `docs/superpowers/plans/roadmap.md`

## Global Constraints

- Bens e direitos: custo de aquisição em BRL (não valor de mercado) — PTAX do dia de cada compra já congelada (`cost_brl_total` de `PositionService`).
- Caixa: saldo USD convertido pela PTAX do último dia útil do ano (recuo automático já implementado).
- Rendimentos/ganhos: seção espelha `TaxEngine.compute()` (taxa 15%, crédito withholding, devido).
- PDF gerado localmente (reportlab), nada externo.
- `Decimal` sempre; formatação pt-br só na renderização.

---

### Task 1: Filtro `until` em PositionService e CashLedgerService

**Files:**
- Modify: `ledger/position.py`, `ledger/cash.py`
- Test: `tests/ledger/test_until_filter.py`

**Interfaces:**
- Produces: `PositionService.position(account, asset, until=None)` e `CashLedgerService.balance(account, until=None)` (já tem) — `until` restringe a eventos `trade_date__lte=until`.

- [ ] **Step 1: Testes falhando**

```python
from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from ledger.cash import CashLedgerService
from ledger.models import Asset, BrokerAccount
from ledger.position import PositionService
from ledger.service import EventService

RATE = Decimal("5.00000000")


@pytest.fixture
def acct_asset(db):
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="STOCK")
    return acct, asset


def _record(acct, **kw):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(dict(account=acct, **kw))


@pytest.mark.django_db
def test_position_until_excludes_later_buys(acct_asset):
    acct, asset = acct_asset
    _record(acct, event_type="BUY", asset=asset, trade_date=date(2026, 1, 5), quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(0))
    _record(acct, event_type="BUY", asset=asset, trade_date=date(2026, 12, 20), quantity=Decimal(5), price_usd=Decimal(100), fee_usd=Decimal(0))
    pos = PositionService().position(acct, asset, until=date(2026, 12, 31))
    assert pos["quantity"] == Decimal(15)
    pos_jun = PositionService().position(acct, asset, until=date(2026, 6, 30))
    assert pos_jun["quantity"] == Decimal(10)


@pytest.mark.django_db
def test_cash_until(acct, db):
    _record(acct, event_type="APORTE", trade_date=date(2026, 1, 2), amount_usd=Decimal(5000))
    _record(acct, event_type="APORTE", trade_date=date(2026, 12, 31), amount_usd=Decimal(1000))
    assert CashLedgerService().balance(acct, until=date(2026, 6, 30)) == Decimal(5000)
```

- [ ] **Step 2: FAIL** → **Step 3: implementar** (`events.filter(trade_date__lte=until)` quando `until`) → **Step 4: PASS** → **Step 5: Commit** `feat: filtro until em posição e caixa`

---

### Task 2: ReportService — estrutura do relatório

**Files:**
- Create: `fiscal/report.py`
- Test: `tests/fiscal/test_report.py`

**Interfaces:**
- Consumes: `PositionService.position(until)`, `CashLedgerService.balance(until)`, `TaxEngine.compute()`, `PtaxService.get_rate(31/12)` (recuo automático p/ último dia útil), `BrokerAccount`
- Produces: `ReportService(year).build() -> dict` com chaves:
  - `year`, `identification`: lista de contas (`broker_name`, `account_number`, `country_code`);
  - `assets`: por ativo com posição ≠ 0 em 31/12: `ticker`, `description`, `asset_type`, `quantity`, `avg_cost_usd`, `cost_brl_total` (custo de aquisição BRL — ficha Bens e Direitos);
  - `cash`: por conta `balance_usd` e `balance_brl` (PTAX 31/12);
  - `income`: resultado do `TaxEngine` (renda, crédito, devido);
  - `ptax_yearend`: a cotação usada (auditoria).

- [ ] **Step 1: Testes falhando** — cenário: aporte 5.000; compra 10 AAPL @100 fee 1; venda 10 @110 fee 1 (posição zero — não aparece); compra 4 MSFT @200 (posição 4). PTAX mockada 5 (31/12 igual). Esperado: `assets` só MSFT qty 4, custo BRL = (800×5)=4000; `cash.balance_usd` = 5000-1001+1099-801 = 4297; `cash.balance_brl` = 21485.

```python
from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from fiscal.report import ReportService
from fiscal.models import TaxRule
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService
from fx.service import PtaxService

RATE = Decimal("5.00000000")


@pytest.fixture
def setup(db):
    TaxRule.objects.create(tax_year=2026, rule_version="V2",
                           brackets=[{"limit_brl": None, "rate": "0.15"}],
                           confirmed=True, effective_from="2026-01-01", effective_until="2026-12-31")
    acct = BrokerAccount.objects.create(broker_name="Avenue Securities LLC", account_number="123")
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="STOCK")
    msft = Asset.objects.create(ticker="MSFT", description="Microsoft", asset_type="STOCK")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(account=acct, event_type="APORTE", trade_date=date(2026, 1, 2), amount_usd=Decimal(5000)))
        EventService().record(dict(account=acct, event_type="BUY", asset=aapl, trade_date=date(2026, 1, 3), quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(1)))
        EventService().record(dict(account=acct, event_type="SELL", asset=aapl, trade_date=date(2026, 6, 1), quantity=Decimal(10), price_usd=Decimal(110), fee_usd=Decimal(1)))
        EventService().record(dict(account=acct, event_type="BUY", asset=msft, trade_date=date(2026, 3, 1), quantity=Decimal(4), price_usd=Decimal(200), fee_usd=Decimal(1)))
    return acct


@pytest.mark.django_db
def test_build_report(setup):
    acct = setup
    with mock.patch.object(PtaxService, "get_rate") as get_rate:
        get_rate.return_value = mock.Mock(rate=RATE, effective_date=date(2026, 12, 31))
        report = ReportService(2026).build()
    assert report["year"] == 2026
    tickers = [a["ticker"] for a in report["assets"]]
    assert tickers == ["MSFT"]  # AAPL posição zero não entra
    assert report["assets"][0]["quantity"] == Decimal(4)
    assert report["cash"][0]["balance_usd"] == Decimal("4297.00000000")
    assert report["cash"][0]["balance_brl"] == Decimal("21485.00000000")
    assert report["income"]["tax_due_brl"] == Decimal("81.00")  # ganho AAPL 98×5=490 × 15%
```

- [ ] **Step 2: FAIL** → **Step 3: implementar** `fiscal/report.py` (itera contas × ativos com eventos; filtra posição ≠ 0 em 31/12; PTAX 31/12 via `PtaxService().get_rate(date(year, 12, 31))`) → **Step 4: PASS** → **Step 5: Commit** `feat: ReportService estrutura do relatório DIRPF`

---

### Task 3: PDF com reportlab

**Files:**
- Create: `fiscal/pdf.py`, adicionar `reportlab==4.2.5` ao `requirements.txt` (reinstalar no venv)
- Test: `tests/fiscal/test_pdf.py`

**Interfaces:**
- Produces: `render_pdf(report: dict) -> bytes`. Seções na ordem: Identificação (contas), Caixa, Bens e Direitos (tabela por ativo), Rendimentos e Ganhos (números do TaxEngine). Rodapé: "Documento de conferência — não substitui a declaração oficial".

- [ ] **Step 1: Teste falhando**

```python
import io
from pypdf import PdfReader  # adicionar pypdf==5.1.0 ao requirements-dev
from fiscal.pdf import render_pdf


def test_render_pdf_contains_sections():
    report = {
        "year": 2026,
        "identification": [{"broker_name": "Avenue", "account_number": "123", "country_code": "US"}],
        "assets": [{"ticker": "MSFT", "description": "Microsoft", "quantity": 4,
                    "avg_cost_usd": 200, "cost_brl_total": 4000}],
        "cash": [{"account": mock.Mock(broker_name="Avenue", account_number="123"),
                  "balance_usd": 4297, "balance_brl": 21485}],
        "income": {"income_brl": 540, "tax_brl": 81, "withholding_credit_brl": 5,
                   "tax_due_brl": 76, "loss_carryforward_brl": 0},
        "ptax_yearend": {"rate": 5, "effective_date": "2026-12-31"},
    }
    pdf_bytes = render_pdf(report)
    text = PdfReader(io.BytesIO(pdf_bytes)).pages[0].extract_text()
    assert "Bens e Direitos" in text
    assert "MSFT" in text
    assert "Imposto devido" in text
```

(mock importado de `unittest.mock`.)

- [ ] **Step 2: FAIL** → **Step 3: implementar** com `reportlab.platypus` (SimpleDocTemplate, Paragraphs, Tables) escrevendo em `io.BytesIO` → **Step 4: PASS** → **Step 5: Commit** `feat: render_pdf com reportlab`

---

### Task 4: Tela de conferência + download

**Files:**
- Create: `fiscal/views.py` (adicionar `ReportView`, `ReportPdfView`), `fiscal/templates/fiscal/report.html`
- Modify: `fiscal/urls.py`, `ledger/templates/ledger/base.html`
- Test: `tests/fiscal/test_report_view.py`

**Interfaces:**
- Produces: `/relatorio/<int:year>/` (HTML de conferência com as 4 seções + link "Baixar PDF") e `/relatorio/<int:year>/pdf` (HttpResponse com `content_type="application/pdf"` e `Content-Disposition: attachment`). Mock da PTAX 31/12 nos testes.

- [ ] **Step 1: Testes falhando** — GET HTML contém "Bens e Direitos" e "MSFT"; GET pdf retorna 200 com `%PDF` no início.
- [ ] **Step 2: FAIL** → **Step 3: implementar** views + template reutilizando `base.html` → **Step 4: PASS** (suite completa) → **Step 5: Commit** `feat: tela de conferência e download do relatório DIRPF`

---

## Self-review

- **Cobertura do roadmap**: relatório com identificação ✓, caixa ✓, bens e direitos (custo BRL) ✓, rendimentos e ganhos ✓; PDF ✓; PTAX 31/12 auditável ✓.
- **Pendente de contador**: códigos da ficha Bens e Direitos, tratamento de custo médio na baixa, PTAX de compra vs 31/12.
- Fim da sequência: com os 4 planos, o fluxo completo (lançar → apurar → relatar) está fechado.
