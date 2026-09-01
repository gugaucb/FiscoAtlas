# Apuração Anual (Plano 3/4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Motor de apuração anual (Lei 14.754/2023 — 15% flat sobre rendimentos de aplicações financeiras no exterior, crédito de withholding limitado por rendimento, compensação de prejuízos do mesmo ano e carryforward pendente de validação) + tela `/apuracao/<ano>/` com memória de cálculo completa.

**Architecture:** App `fiscal` estendido: `AnnualAssessment` (resultado versionado da apuração por ano) + `TaxEngine` (serviço puro que lê eventos ativos e produz a apuração). A tela consulta o `TaxEngine` e persiste snapshot em `AnnualAssessment`.

**Tech Stack:** Django 5, pytest-django, venv local. `.venv/bin/pytest`.

**Legislação:** ver `docs/adr/0003-regras-lei-14754-2023.md` (Lei 14.754/2023, art. 2º §1º, art. 4º, art. 9º, art. 10). Todas as regras `confirmed=False` até validação com contador.

**Spec:** `docs/superpowers/plans/roadmap.md`, `docs/adr/0003-regras-lei-14754-2023.md`

## Global Constraints

- Base de cálculo anual = soma BRL (dos `amount_brl` congelados) de: ganhos em vendas (posicional, via `PositionService.realized`), dividendos, juros de caixa remunerado. Caixa não remunerado (APORTE) não gera fato gerador (art. 10).
- Alíquota única 15% (TaxRule V2 do ano); sem deduções.
- Crédito do withholding: por evento de rendimento, `credit = min(tax_brl_do_evento, 15% do valor bruto do evento)`; total do ano = soma dos créditos (art. 4º).
- Prejuízos: vendas com ganho negativo geram perda; perdas do ano compensam rendimentos do ano; saldo positivo de prejuízo vira `loss_carryforward` disponível para o ano seguinte (art. 9º — flag pendente de contador).
- Apuração é **snapshot versionado**: recalculada sempre; `AnnualAssessment` guarda o resultado para auditoria/relatório.
- `Decimal` sempre.

---

### Task 1: Correção do seed — TaxRule V2 (15% flat, Lei 14.754/2023)

**Files:**
- Modify: `fiscal/management/commands/seed_tax_rules.py`
- Test: `tests/fiscal/test_seed_tax_rules.py` (atualizar)

**Interfaces:**
- Produces: seed cria, para 2024–2026, `rule_version="V2"` com `brackets=[{"limit_brl": None, "rate": "0.15"}]`, `flat_rate=True` via brackets, `confirmed=False`, referenciando ADR-0003. V1 continua no banco (histórico, nunca apagar).

- [ ] **Step 1: Atualizar teste** — seed cria V2 para cada ano; `TaxRule.objects.for_year(2026)` com regra confirmada retorna a V2 quando ambas confirmadas (aproveita teste existente de versões).

```python
@pytest.mark.django_db
def test_seed_creates_v2_flat_15_percent():
    from django.core.management import call_command
    call_command("seed_tax_rules")
    v2 = TaxRule.objects.filter(tax_year=2026, rule_version="V2").first()
    assert v2 is not None
    assert v2.brackets == [{"limit_brl": None, "rate": "0.15"}]
    assert not v2.confirmed
    assert TaxRule.objects.filter(tax_year=2024, rule_version="V2").exists()
```

Manter testes antigos adaptados: contagem idempotente vira 6 (3 anos × 2 versões).

- [ ] **Step 2: Rodar, verificar FAIL**
- [ ] **Step 3: Implementar** — no comando, adicionar defaults V2:

```python
for year in (2024, 2025, 2026):
    TaxRule.objects.get_or_create(tax_year=year, rule_version="V1", defaults={...})  # igual hoje
    TaxRule.objects.get_or_create(
        tax_year=year, rule_version="V2",
        defaults={
            "brackets": [{"limit_brl": None, "rate": "0.15"}],
            "fx_cash_policy": {"non_bearing_cash_exempt": True},
            "quote_type": "VENDA",
            "confirmed": False,
            "effective_from": f"{year}-01-01",
            "effective_until": f"{year}-12-31",
            "notes": "Lei 14.754/2023 — ver ADR-0003",
        },
    )
```

(Adicionar campo `notes` a TaxRule com migration.)

- [ ] **Step 4: Rodar, verificar PASS** — suite fiscal.
- [ ] **Step 5: Commit** — `git commit -m "feat: seed V2 15% flat Lei 14.754/2023 (ADR-0003)"`

---

### Task 2: TaxEngine — agregação anual de rendimentos

**Files:**
- Create: `fiscal/engine.py`
- Test: `tests/fiscal/test_tax_engine.py`

**Interfaces:**
- Consumes: `FinancialEvent`, `PositionService.realized`, `PtaxService` (PTAX de cada evento já congelada)
- Produces: `TaxEngine(assessment_year: int).compute() -> dict` com:
  - `income_brl`: soma BRL de dividendos + juros + ganhos líquidos de vendas (eventos ativos do ano);
  - `loss_brl`: soma BRL de perdas em vendas (valor absoluto);
  - `withholding_credit_brl`: soma dos créditos limitados (min(tax_brl, 15% × bruto do rendimento));
  - `taxable_brl`: `income_brl - loss_brl` (≥ 0; excesso de perda vira carryforward);
  - `tax_brl`: `taxable_brl * 0.15` (lido dos brackets da TaxRule V2 — alíquota da faixa final);
  - `tax_due_brl`: `max(tax_brl - withholding_credit_brl, 0)`;
  - `loss_carryforward_brl`: perdas não compensadas no ano;
  - `detail`: lista por evento (ticker, data, bruto BRL, withholding BRL, crédito usado) para a memória de cálculo.

- [ ] **Step 1: Testes falhando** — cenário: aporte 5.000 USD; compra 10 AAPL @100; venda 10 @110 (ganho 99 USD); dividendo com withholding 1 USD sobre 10 USD. PTAX 5. Ganho venda = 99×5=495 BRL; dividendo bruto 50 BRL, withholding 5 BRL, crédito 5; renda total 545; imposto 81,75; devido 76,75.

```python
from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from fiscal.engine import TaxEngine
from fiscal.models import TaxRule
from ledger.models import Asset, BrokerAccount

RATE = Decimal("5.00000000")


@pytest.fixture
def setup(db):
    TaxRule.objects.create(tax_year=2026, rule_version="V2",
                           brackets=[{"limit_brl": None, "rate": "0.15"}],
                           confirmed=True, effective_from="2026-01-01", effective_until="2026-12-31")
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="STOCK")
    return acct, asset


def _record(acct, **kw):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(dict(account=acct, **kw))


@pytest.mark.django_db
def test_full_year_computation(setup):
    acct, asset = setup
    _record(acct, event_type="APORTE", trade_date=date(2026, 1, 2), amount_usd=Decimal(5000))
    _record(acct, event_type="BUY", asset=asset, trade_date=date(2026, 1, 3),
            quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(1))
    _record(acct, event_type="SELL", asset=asset, trade_date=date(2026, 6, 1),
            quantity=Decimal(10), price_usd=Decimal(110), fee_usd=Decimal(1))
    _record(acct, event_type="DIVIDEND", asset=asset, trade_date=date(2026, 6, 15),
            quantity=Decimal(10), per_share_usd=Decimal(1), tax_usd=Decimal(1))
    result = TaxEngine(2026).compute()
    assert result["income_brl"] == Decimal("545.00")
    assert result["withholding_credit_brl"] == Decimal("5.00")
    assert result["tax_brl"] == Decimal("81.75")
    assert result["tax_due_brl"] == Decimal("76.75")


@pytest.mark.django_db
def test_loss_generates_carryforward(setup):
    acct, asset = setup
    _record(acct, event_type="APORTE", trade_date=date(2026, 1, 2), amount_usd=Decimal(5000))
    _record(acct, event_type="BUY", asset=asset, trade_date=date(2026, 1, 3),
            quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(0))
    _record(acct, event_type="SELL", asset=asset, trade_date=date(2026, 6, 1),
            quantity=Decimal(10), price_usd=Decimal(80), fee_usd=Decimal(0))
    result = TaxEngine(2026).compute()
    assert result["taxable_brl"] == Decimal("0")
    assert result["loss_carryforward_brl"] == Decimal("1000.00")  # -200 USD × 5
    assert result["tax_due_brl"] == Decimal("0")
```

- [ ] **Step 2: Rodar, verificar FAIL**
- [ ] **Step 3: Implementar** `fiscal/engine.py`:

```python
from decimal import Decimal
from fiscal.models import TaxRule
from ledger.cash import CashLedgerService  # não usado no cálculo; caixa isento (art. 10)
from ledger.models import FinancialEvent
from ledger.position import PositionService


class TaxEngine:
    RATE = Decimal("0.15")

    def __init__(self, year: int):
        self.year = year

    def compute(self) -> dict:
        rule = TaxRule.objects.for_year(self.year)
        rate = Decimal(rule.brackets[-1]["rate"])
        events = FinancialEvent.objects.filter(
            active=True, trade_date__year=self.year,
            event_type__in=("DIVIDEND", "JUROS", "SELL"),
        ).select_related("asset").order_by("trade_date", "id")

        detail, income, loss, credit = [], Decimal(0), Decimal(0), Decimal(0)
        realized_idx = {}  # por evento SELL
        for acct_id in events.values_list("account_id", flat=True).distinct():
            for asset in events.values_list("asset_id", flat=True).distinct():
                if asset:
                    for r in PositionService().realized(acct_id, asset):
                        if r["event"].trade_date.year == self.year:
                            realized_idx[r["event"].id] = r

        for ev in events:
            if ev.event_type == "SELL":
                r = realized_idx.get(ev.id)
                if r is None:
                    continue
                gain_brl = (r["gain_usd"] * ev.fx_rate).quantize(Decimal("0.01"))
                gross_brl = gain_brl if gain_brl > 0 else Decimal(0)
                if gain_brl < 0:
                    loss += -gain_brl
            else:  # DIVIDEND, JUROS — bruto = (per_share*qty) convertido; withholding separado
                gross_usd = ev.amount_usd + ev.tax_usd
                gross_brl = (gross_usd * ev.fx_rate).quantize(Decimal("0.01"))
                income += gross_brl
                wh_brl = (ev.tax_usd * ev.fx_rate).quantize(Decimal("0.01"))
                used = min(wh_brl, (gross_brl * rate).quantize(Decimal("0.01")))
                credit += used
                detail.append({"event": ev, "gross_brl": gross_brl, "withholding_brl": wh_brl, "credit_used": used})
                continue
            income += gross_brl

        taxable = max(income - loss, Decimal(0))
        excess_loss = max(loss - income, Decimal(0))
        tax = (taxable * rate).quantize(Decimal("0.01"))
        return {
            "income_brl": income, "loss_brl": loss, "taxable_brl": taxable,
            "tax_brl": tax, "withholding_credit_brl": credit,
            "tax_due_brl": max(tax - credit, Decimal(0)),
            "loss_carryforward_brl": excess_loss,
            "detail": detail, "rule": rule,
        }
```

- [ ] **Step 4: Rodar, verificar PASS** — `.venv/bin/pytest tests/fiscal/`
- [ ] **Step 5: Commit** — `git commit -m "feat: TaxEngine apuração anual Lei 14.754/2023"`

---

### Task 3: Modelo AnnualAssessment (snapshot)

**Files:**
- Modify: `fiscal/models.py`
- Test: `tests/fiscal/test_annual_assessment.py`

**Interfaces:**
- Produces: `fiscal.models.AnnualAssessment`: `year` (único), `rule_version`, `income_brl`, `loss_brl`, `taxable_brl`, `tax_brl`, `withholding_credit_brl`, `tax_due_brl`, `loss_carryforward_brl`, `detail` JSONB, `computed_at`, `confirmed: bool` (fechamento). Método de classe `TaxEngine.save_snapshot(year) -> AnnualAssessment` (upsert).

- [ ] **Step 1: Teste falhando** — snapshot criado, campos batem com engine, recomputar atualiza o mesmo registro.
- [ ] **Step 2: FAIL**
- [ ] **Step 3: Implementar** — modelo + `update_or_create(year=..., defaults=...)`.
- [ ] **Step 4: PASS** — suite fiscal.
- [ ] **Step 5: Commit** — `git commit -m "feat: AnnualAssessment snapshot da apuração"`

---

### Task 4: Tela de apuração anual

**Files:**
- Create: `fiscal/views.py`, `fiscal/urls.py`, `fiscal/templates/fiscal/assessment.html`
- Modify: `config/urls.py`
- Test: `tests/fiscal/test_assessment_view.py`

**Interfaces:**
- Produces: rota `/apuracao/<int:year>/` mostrando: rendimentos, perdas, base, imposto 15%, crédito withholding, imposto devido, carryforward, e a memória de cálculo (tabela de `detail` com cada rendimento). Link no nav do `base.html`.

- [ ] **Step 1: Teste falhando** — com os eventos do cenário do Task 2, GET `/apuracao/2026/` contém "76,75" (ou 76.75) e "AAPL".
- [ ] **Step 2: FAIL**
- [ ] **Step 3: Implementar** — view chama `TaxEngine(year).compute()` e renderiza.
- [ ] **Step 4: PASS** — suite completa.
- [ ] **Step 5: Commit** — `git commit -m "feat: tela de apuração anual com memória de cálculo"`

---

## Self-review

- **Cobertura**: 15% flat (ADR-0003 item 1–2) ✓; crédito limitado por rendimento (item 3) ✓; perdas + carryforward (item 4) ✓; caixa isento (item 5) ✓; memória de cálculo para o relatório (Plano 4) ✓.
- **Pendente de contador** (explícito no código/plano): compensabilidade de prejuízos em anos futuros, taxa de tratado para withholding, confirmação das TaxRule.
- **Contratos para o Plano 4**: `AnnualAssessment` (snapshot), `TaxEngine.compute() -> dict`, `detail` por evento.
