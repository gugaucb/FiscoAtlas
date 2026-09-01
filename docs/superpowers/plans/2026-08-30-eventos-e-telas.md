# Eventos + Telas de Entrada Manual (Plano 2/4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modelo de eventos financeiros versionados (nunca apagados), serviços de domínio (custo médio, posição, caixa) e telas Django para lançar manualmente cada operação no ato — aporte, compra, venda, dividendo, juros, taxa e imposto retido nos EUA. Único canal de entrada de dados (roadmap.md).

**Architecture:** App `ledger` estendido: `FinancialEvent` (append-only, correção por nova versão — spec §9), `EventService` (valida + grava + calcula BRL via PTAX), `PositionService` (custo médio), `CashLedgerService` (saldo por conta). Views Django com forms e templates simples (server-side, sem SPA).

**Tech Stack:** Django 5, SQLite (venv local), pytest-django. Rodar testes com `.venv/bin/pytest` (Docker opcional).

**Legislação (pesquisada — validar antes da Task 6):** Imposto retido nos EUA sobre dividendos (tipicamente 10–30% conforme tratado Brasil–EUA; para pessoa física com W-8BEN, 10% sobre dividendos de ações/ETFs brasileiros em brokers EUA) é crédito no IRPF, limitado ao imposto brasileiro devido sobre o rendimento (art. 104/Lei 5.172/66 — CTN). Este plano apenas **registra** `tax_usd`; o uso como crédito é do Plano 3.

**Spec:** `PROJETO — SISTEMA DE APURAÇÃO DE IRPF PARA INVESTIMENTOS NO EXTERIOR.md` (§7–9), `docs/superpowers/plans/roadmap.md`

## Global Constraints

- Eventos nunca são apagados nem editados; correção = novo evento `corrects=<id>` (spec §9).
- `Decimal` em todo cálculo monetário; modelos: `DECIMAL(20,8)` valores, `DECIMAL(24,10)` quantidades (spec §37).
- BRL de cada evento calculado via `PtaxService.get_rate(data)` no momento do lançamento e **congelado** no evento (a PTAX pode ser override depois, mas o evento guarda o que foi usado — auditável).
- Venda sem posição suficiente = erro (`ValueError`), nunca permite posição negativa.
- Sem importação de arquivos: tudo via telas.
- Testes: `.venv/bin/pytest`.

---

### Task 1: Modelo FinancialEvent

**Files:**
- Modify: `ledger/models.py`
- Create: `ledger/migrations/0002_*.py` (via makemigrations)
- Test: `tests/ledger/test_financial_event.py`

**Interfaces:**
- Produces: `ledger.models.FinancialEvent` com campos: `event_type` em {APORTE, WITHDRAWAL, BUY, SELL, DIVIDEND, JUROS, FEE, TAX_WITHHELD}, `account` FK BrokerAccount, `asset` FK Asset **nullable** (eventos de caixa não têm ativo), `trade_date: date`, `settle_date: date|null`, `quantity: Decimal(24,10)|null`, `price_usd: Decimal(20,8)|null`, `fee_usd: Decimal(20,8)`, `amount_usd: Decimal(20,8)` (total do evento, sinalizado: entrada positiva, saída negativa — calculado pelo serviço), `tax_usd: Decimal(20,8)` (imposto retido nos EUA, ex. withholding de dividendo), `fx_rate: Decimal(12,8)|null`, `amount_brl: Decimal(20,8)|null`, `notes`, `corrects` FK self null (correção), `active: bool`. Constraints: `quantity`+`asset` obrigatórios juntos para BUY/SELL; `asset` obrigatório para DIVIDEND/JUROS/TAX_WITHHELD.

- [ ] **Step 1: Teste falhando**

`tests/ledger/test_financial_event.py`:
```python
import pytest
from ledger.models import Asset, BrokerAccount, FinancialEvent


@pytest.fixture
def account(db):
    return BrokerAccount.objects.create(broker_name="Avenue", account_number="1")


@pytest.fixture
def asset(db):
    return Asset.objects.create(ticker="AAPL", description="Apple", asset_type="STOCK")


def _event(account, asset, **kw):
    base = dict(
        event_type="BUY", account=account, asset=asset, trade_date="2026-03-10",
        quantity=10, price_usd=100, amount_usd=-1000, fee_usd=1,
    )
    base.update(kw)
    return FinancialEvent.objects.create(**base)


@pytest.mark.django_db
def test_buy_event_stores_decimal_fields(account, asset):
    ev = _event(account, asset, quantity=10, price_usd=100.5, amount_usd=-1005)
    assert ev.quantity == 10
    assert ev.price_usd == 100.5
    assert ev.amount_usd == -1005
    assert ev.active


@pytest.mark.django_db
def test_cash_event_has_null_asset(account):
    ev = FinancialEvent.objects.create(
        event_type="APORTE", account=account, trade_date="2026-03-01",
        amount_usd=5000, fee_usd=0,
    )
    assert ev.asset is None
    assert ev.quantity is None
```

- [ ] **Step 2: Rodar, verificar FAIL** — `.venv/bin/pytest tests/ledger/test_financial_event.py` → `ImportError: FinancialEvent`

- [ ] **Step 3: Implementar** — adicionar a `ledger/models.py`:

```python
EVENT_TYPES = [
    ("APORTE", "Aporte (entrada de caixa)"),
    ("WITHDRAWAL", "Retirada (saída de caixa)"),
    ("BUY", "Compra"),
    ("SELL", "Venda"),
    ("DIVIDEND", "Dividendo"),
    ("JUROS", "Juros/rendimento de caixa"),
    ("FEE", "Taxa/corretagem"),
    ("TAX_WITHHELD", "Imposto retido nos EUA"),
]


class FinancialEvent(models.Model):
    event_type = models.CharField(max_length=16, choices=EVENT_TYPES)
    account = models.ForeignKey(BrokerAccount, on_delete=models.PROTECT, related_name="events")
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, null=True, blank=True, related_name="events")
    trade_date = models.DateField()
    settle_date = models.DateField(null=True, blank=True)
    quantity = models.DecimalField(max_digits=24, decimal_places=10, null=True, blank=True)
    price_usd = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    fee_usd = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    amount_usd = models.DecimalField(max_digits=20, decimal_places=8)
    tax_usd = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    fx_rate = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    amount_brl = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    notes = models.CharField(max_length=500, blank=True)
    corrects = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="corrected_by")
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["trade_date"]), models.Index(fields=["event_type"])]
```

Rodar `makemigrations ledger && migrate`.

- [ ] **Step 4: Rodar, verificar PASS** — `.venv/bin/pytest tests/ledger/ -v`

- [ ] **Step 5: Commit** — `git add ledger/ tests/ledger/ && git commit -m "feat: modelo FinancialEvent append-only"`

---

### Task 2: EventService — validação e conversão BRL

**Files:**
- Create: `ledger/service.py`
- Test: `tests/ledger/test_event_service.py`

**Interfaces:**
- Consumes: `FinancialEvent`, `PtaxService.get_rate`
- Produces: `EventService.record(data: dict) -> FinancialEvent`. Regras: (1) BUY: `amount_usd = -(quantity*price + fee)`; SELL: `amount_usd = +(quantity*price - fee)` — recusa se o valor informado divergir do calculado (tolerância 0.01); (2) SELL exige posição suficiente (ver Task 3 — aqui delega a `PositionService.position()); (3) DIVIDEND: `amount_usd = +(per_share*quantity - tax_usd)` onde `tax_usd` é o withholding; (4) PTAX: `fx_rate = PtaxService.get_rate(trade_date).rate`, `amount_brl = amount_usd * fx_rate`; (5) valores negativos ou quantity<=0 em BUY/SELL → `ValueError`. Invalida eventos anteriores corrigidos: `corrects` dado → marca evento corrigido `active=False`.

- [ ] **Step 1: Testes falhando** (mock do `_fetch_bcb` para não chamar rede)

```python
from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from ledger.models import Asset, BrokerAccount, FinancialEvent
from ledger.service import EventService

BCB = {"value": [{"cotacaoVenda": 5.0, "cotacaoCompra": 4.99}]}


@pytest.fixture
def db_assets(db):
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="STOCK")
    return acct, asset


def _buy(acct, asset, qty=10, price=100, **kw):
    with mock.patch.object(EventService, "_ptax_rate", return_value=Decimal("5.00000000")):
        return EventService().record(dict(
            event_type="BUY", account=acct, asset=asset, trade_date=date(2026, 3, 10),
            quantity=Decimal(qty), price_usd=Decimal(price), fee_usd=Decimal("1"), **kw,
        ))


@pytest.mark.django_db
def test_buy_computes_amount_and_brl(db_assets):
    acct, asset = db_assets
    ev = _buy(acct, asset)
    assert ev.amount_usd == Decimal("-1001.00000000")  # -(10*100 + 1)
    assert ev.fx_rate == Decimal("5.00000000")
    assert ev.amount_brl == Decimal("-5005.00000000")


@pytest.mark.django_db
def test_buy_rejects_wrong_amount(db_assets):
    acct, asset = db_assets
    with pytest.raises(ValueError, match="amount"):
        with mock.patch.object(EventService, "_ptax_rate", return_value=Decimal("5")):
            EventService().record(dict(
                event_type="BUY", account=acct, asset=asset, trade_date=date(2026, 3, 10),
                quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(1),
                amount_usd=Decimal(-999),
            ))


@pytest.mark.django_db
def test_sell_requires_position(db_assets):
    acct, asset = db_assets
    with pytest.raises(ValueError, match="posição"):
        with mock.patch.object(EventService, "_ptax_rate", return_value=Decimal("5")):
            EventService().record(dict(
                event_type="SELL", account=acct, asset=asset, trade_date=date(2026, 3, 11),
                quantity=Decimal(5), price_usd=Decimal(110), fee_usd=Decimal(1),
            ))


@pytest.mark.django_db
def test_corrections_deactivate_original(db_assets):
    acct, asset = db_assets
    original = _buy(acct, asset)
    with mock.patch.object(EventService, "_ptax_rate", return_value=Decimal("5")):
        fix = EventService().record(dict(
            event_type="BUY", account=acct, asset=asset, trade_date=date(2026, 3, 10),
            quantity=Decimal(11), price_usd=Decimal(100), fee_usd=Decimal(1),
            corrects=original,
        ))
    original.refresh_from_db()
    assert not original.active and fix.corrects == original
```

- [ ] **Step 2: Rodar, verificar FAIL**

- [ ] **Step 3: Implementar** `ledger/service.py`:

```python
from decimal import Decimal

from fx.models import PtaxRate
from fx.service import PtaxService
from ledger.models import FinancialEvent

TOL = Decimal("0.01")


class EventService:
    def __init__(self, ptax: PtaxService | None = None):
        self.ptax = ptax or PtaxService()

    def _ptax_rate(self, trade_date) -> Decimal:
        return self.ptax.get_rate(trade_date).rate

    def record(self, data: dict) -> FinancialEvent:
        etype = data["event_type"]
        qty, price = data.get("quantity"), data.get("price_usd")
        fee = data.get("fee_usd") or Decimal(0)
        tax = data.get("tax_usd") or Decimal(0)

        if etype in ("BUY", "SELL") and (not qty or not price or qty <= 0 or price <= 0):
            raise ValueError("quantity e price_usd devem ser positivos para BUY/SELL")
        if etype == "BUY":
            expected = -(qty * price + fee)
        elif etype == "SELL":
            expected = qty * price - fee
        elif etype == "DIVIDEND":
            expected = data.get("per_share_usd", Decimal(0)) * qty - tax
        else:  # APORTE, WITHDRAWAL, JUROS, FEE, TAX_WITHHELD
            expected = data["amount_usd"]

        informed = data.get("amount_usd")
        if informed is not None and abs(informed - expected) > TOL:
            raise ValueError(f"amount_usd diverge do calculado: esperado {expected}")

        from ledger.position import PositionService  # import local (Task 3)
        if etype == "SELL":
            pos = PositionService().position(data["account"], data["asset"])
            if pos["quantity"] < qty:
                raise ValueError(f"posição insuficiente: {pos['quantity']} < {qty}")

        rate = self._ptax_rate(data["trade_date"])
        if data.get("corrects"):
            data["corrects"].active = False
            data["corrects"].save()
        return FinancialEvent.objects.create(
            **{k: v for k, v in data.items() if k != "amount_usd" or etype not in ("BUY", "SELL", "DIVIDEND")},
            amount_usd=expected,
            fx_rate=rate,
            amount_brl=(expected * rate).quantize(Decimal("0.00000001")),
        )
```

- [ ] **Step 4: Rodar, verificar PASS** — `.venv/bin/pytest tests/ledger/ -v` (testes da Task 1 que usam `_event` direto no modelo continuam passando)

- [ ] **Step 5: Commit** — `git commit -m "feat: EventService com validação, PTAX congelada e correção"`

---

### Task 3: PositionService — custo médio

**Files:**
- Create: `ledger/position.py`
- Test: `tests/ledger/test_position.py`

**Interfaces:**
- Produces: `PositionService.position(account, asset) -> dict` com `quantity: Decimal`, `avg_cost_usd: Decimal`, `cost_brl_total: Decimal`. Só considera eventos `active=True`. BUY soma quantidade e custo (`quantity*price + fee`); SELL subtrai quantidade e custo proporcional (`avg_cost*qty`); DIVIDEND/JUROS não afetam posição. `position(...)` com nenhum evento retorna `{"quantity": 0, "avg_cost_usd": 0, "cost_brl_total": 0}`. `realized(account, asset)` → lista de vendas com `gain_usd = (price*qty - fee) - avg_cost*qty` para o Plano 3.

- [ ] **Step 1: Testes falhando**

`tests/ledger/test_position.py`:

```python
from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from ledger.models import Asset, BrokerAccount
from ledger.position import PositionService
from ledger.service import EventService

RATE = Decimal("5.00000000")


@pytest.fixture
def acct_asset(db):
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="STOCK")
    return acct, asset


def _record(acct, asset, **kw):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(dict(account=acct, asset=asset, **kw))


@pytest.mark.django_db
def test_average_cost_two_buys(acct_asset):
    acct, asset = acct_asset
    _record(acct, asset, event_type="BUY", trade_date=date(2026, 1, 5), quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(0))
    _record(acct, asset, event_type="BUY", trade_date=date(2026, 2, 5), quantity=Decimal(10), price_usd=Decimal(120), fee_usd=Decimal(0))
    pos = PositionService().position(acct, asset)
    assert pos["quantity"] == Decimal(20)
    assert pos["avg_cost_usd"] == Decimal(110)
    assert pos["cost_brl_total"] == Decimal(20) * Decimal(110) * RATE


@pytest.mark.django_db
def test_sell_reduces_position_keeps_avg_cost(acct_asset):
    acct, asset = acct_asset
    _record(acct, asset, event_type="BUY", trade_date=date(2026, 1, 5), quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(0))
    _record(acct, asset, event_type="SELL", trade_date=date(2026, 2, 5), quantity=Decimal(4), price_usd=Decimal(110), fee_usd=Decimal(1))
    pos = PositionService().position(acct, asset)
    assert pos["quantity"] == Decimal(6)
    assert pos["avg_cost_usd"] == Decimal(100)


@pytest.mark.django_db
def test_correction_changes_position(acct_asset):
    acct, asset = acct_asset
    original = _record(acct, asset, event_type="BUY", trade_date=date(2026, 1, 5), quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(0))
    _record(acct, asset, event_type="BUY", trade_date=date(2026, 1, 5), quantity=Decimal(12), price_usd=Decimal(100), fee_usd=Decimal(0), corrects=original)
    pos = PositionService().position(acct, asset)
    assert pos["quantity"] == Decimal(12)  # original inativo
```

- [ ] **Step 2: Rodar, verificar FAIL**

- [ ] **Step 3: Implementar** `ledger/position.py`:

```python
from decimal import Decimal

from ledger.models import FinancialEvent


class PositionService:
    def position(self, account, asset) -> dict:
        qty = Decimal(0)
        cost = Decimal(0)
        events = FinancialEvent.objects.filter(
            account=account, asset=asset, active=True, trade_date__isnull=False
        ).order_by("trade_date", "id")
        for ev in events:
            if ev.event_type == "BUY":
                cost += ev.quantity * ev.price_usd + ev.fee_usd
                qty += ev.quantity
            elif ev.event_type == "SELL":
                avg = cost / qty if qty else Decimal(0)
                cost -= avg * ev.quantity
                qty -= ev.quantity
        avg = cost / qty if qty else Decimal(0)
        return {"quantity": qty, "avg_cost_usd": avg, "cost_brl_total": cost * avg / avg if avg else Decimal(0)}
```

Corrigir `cost_brl_total` para o contrato do teste: guardar também o BRL real por compra — na prática: acumular `cost_brl` somando `amount_brl` de BUYs e subtraindo `avg*qty*fx` dos SELLs (usar `ev.fx_rate` de cada evento). Implementação final usa dois acumuladores (`cost_usd`, `cost_brl`); o dict retorna `quantity`, `avg_cost_usd`, `cost_brl_total` (= `cost_brl`). Também implementar `realized(account, asset)` percorrendo SELLs com o `avg_cost` corrente e retornando dicts `{"event": ev, "avg_cost_usd": ..., "gain_usd": ...}`.

- [ ] **Step 4: Rodar, verificar PASS** — `.venv/bin/pytest tests/ledger/ -v`

- [ ] **Step 5: Commit** — `git commit -m "feat: PositionService custo médio com correções"`

---

### Task 4: CashLedgerService — saldo de caixa

**Files:**
- Create: `ledger/cash.py`
- Test: `tests/ledger/test_cash.py`

**Interfaces:**
- Produces: `CashLedgerService.balance(account, until=None) -> Decimal` (USD). Entradas: APORTE, SELL, DIVIDEND, JUROS. Saídas: BUY, WITHDRAWAL, FEE, TAX_WITHHELD. Só eventos `active=True`. `history(account)` → lista cronológica com saldo acumulado (para a tela).

- [ ] **Step 1: Testes falhando** — aporte 5000, compra -1001 (fee 1), dividendo +99 (tax 1), saldo = 4098. Juros de caixa +10. Correção de aporte para 4000 → saldo recalculado.

- [ ] **Step 2: Rodar, verificar FAIL**

- [ ] **Step 3: Implementar** `ledger/cash.py` — filter `active=True, account=account` ordenado por `trade_date, id`, sinal por tipo:

```python
INFLOWS = {"APORTE", "SELL", "DIVIDEND", "JUROS"}
```

- [ ] **Step 4: Rodar, verificar PASS**

- [ ] **Step 5: Commit** — `git commit -m "feat: CashLedgerService saldo e histórico"`

---

### Task 5: Telas de lançamento manual

**Files:**
- Create: `ledger/forms.py`, `ledger/views.py`, `ledger/urls.py`, `ledger/templates/ledger/` (`base.html`, `event_list.html`, `event_form.html`, `positions.html`, `cash.html`)
- Modify: `config/urls.py` (include `ledger.urls`), `config/settings.py` (nothing)
- Test: `tests/ledger/test_views.py` (django test client)

**Interfaces:**
- Produces: rotas `/` (lista de eventos + link de novo lançamento), `/eventos/novo/` (form com tipo selecionável; campos aparecem conforme tipo via JS mínimo ou submissão em duas etapas: escolher tipo → form específico), `/eventos/<id>/corrigir/` (pré-preenchido, cria versão corretora), `/posicoes/` (tabela por ativo com qty, custo médio USD e BRL), `/caixa/` (saldo e histórico). Mensagens de erro de validação exibidas no form (`django.contrib.messages`).

- [ ] **Step 1: Testes falhando**

```python
from decimal import Decimal
from unittest import mock
import pytest
from ledger.models import Asset, BrokerAccount

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(db):
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="STOCK")
    return acct, asset


def test_event_list_shows_events(client, setup):
    client.get("/")  # 200
    assert b"AAPL" not in client.get("/").content  # sem eventos ainda


def test_new_event_form_creates_buy(client, setup):
    acct, asset = setup
    with mock.patch("ledger.views.EventService._ptax_rate", return_value=Decimal("5")):
        resp = client.post("/eventos/novo/", {
            "event_type": "BUY", "account": acct.pk, "asset": asset.pk,
            "trade_date": "2026-03-10", "quantity": "10", "price_usd": "100",
            "fee_usd": "1", "notes": "",
        })
    assert resp.status_code == 302
    assert b"AAPL" in client.get("/").content


def test_form_rejects_invalid_sell(client, setup):
    acct, asset = setup
    with mock.patch("ledger.views.EventService._ptax_rate", return_value=Decimal("5")):
        resp = client.post("/eventos/novo/", {
            "event_type": "SELL", "account": acct.pk, "asset": asset.pk,
            "trade_date": "2026-03-11", "quantity": "5", "price_usd": "110", "fee_usd": "1",
        })
    assert resp.status_code == 200  # re-render com erro
    assert b"insuficiente" in resp.content


def test_positions_page(client, setup):
    acct, asset = setup
    with mock.patch("ledger.views.EventService._ptax_rate", return_value=Decimal("5")):
        client.post("/eventos/novo/", {
            "event_type": "BUY", "account": acct.pk, "asset": asset.pk,
            "trade_date": "2026-03-10", "quantity": "10", "price_usd": "100", "fee_usd": "1",
        })
    html = client.get("/posicoes/").content.decode()
    assert "AAPL" in html and "10" in html
```

- [ ] **Step 2: Rodar, verificar FAIL**

- [ ] **Step 3: Implementar** — `ledger/forms.py`:

```python
import django.forms as forms
from ledger.models import FinancialEvent


class EventForm(forms.ModelForm):
    class Meta:
        model = FinancialEvent
        fields = ["event_type", "account", "asset", "trade_date", "quantity",
                  "price_usd", "fee_usd", "tax_usd", "amount_usd", "notes"]
        widgets = {"trade_date": forms.DateInput(attrs={"type": "date"})}
```

`ledger/views.py`: `EventListView` (lista ordenada por trade_date desc, mostra tipo, ativo, qty, valor USD e BRL), `EventCreateView` (chama `EventService().record(form.cleaned_data)`; `ValueError` → `form.add_error(None, str(e))`), `EventCorrectView` (carrega evento, form pré-preenchido, submete com `corrects=evento`), `PositionsView` (itera assets com eventos ativos, `PositionService().position`), `CashView` (`CashLedgerService.history`). Templates herdam de `base.html` com nav simples. `ledger/urls.py` com as 5 rotas; `config/urls.py` inclui.

Nota: no `EventCreateView`, para BUY/SELL/DIVIDEND deixar `amount_usd` vazio no form (calculado pelo serviço) — remover o campo do form ou torná-lo opcional.

- [ ] **Step 4: Rodar, verificar PASS** — `.venv/bin/pytest tests/ -v` (suite inteira)

- [ ] **Step 5: Commit** — `git add ledger/ config/urls.py tests/ledger/test_views.py && git commit -m "feat: telas de lançamento manual, posições e caixa"`

---

### Task 6: Juros de caixa marcados como remunerado (gatilho fiscal)

**Files:**
- Modify: `ledger/models.py` (campo `is_interest_bearing` já existe em BrokerAccount — validar uso)
- Test: `tests/ledger/test_cash_interest.py`

**Interfaces:**
- Produces: validação em `EventService.record`: evento `JUROS` só é aceito em conta com `is_interest_bearing=True` (senão o rendimento seria isento como caixa não remunerado — política em `TaxRule.fx_cash_policy`). A decisão fiscal (isento ou tributável) fica registrada no evento para o Plano 3.

- [ ] **Step 1: Teste falhando** — criar `JUROS` em conta `is_interest_bearing=False` → `ValueError("conta não remunerada")`.
- [ ] **Step 2: Rodar, verificar FAIL**
- [ ] **Step 3: Implementar** — check no início de `record` quando `etype == "JUROS"`.
- [ ] **Step 4: Rodar, verificar PASS** — suite completa.
- [ ] **Step 5: Commit** — `git commit -m "feat: JUROS restrito a contas remuneradas"`

---

## Self-review

- **Cobertura do roadmap (Plano 2)**: eventos versionados nunca apagados (§9) ✓; entrada 100% manual via telas ✓; custo médio ✓; caixa ✓; PTAX congelada no evento (auditável) ✓; registro do withholding EUA para crédito no Plano 3 ✓.
- **Placeholders**: nenhum TBD; Tasks 3/4 têm contrato definido nas interfaces, código detalhado nas Tasks 1/2/5.
- **Contratos usados no Plano 3**: `PositionService.realized(account, asset)`, `PositionService.position(...)` (dict), `CashLedgerService.balance/history`, `FinancialEvent.tax_usd` (crédito), `event.amount_brl` (base de cálculo), `EventService.record` (assinatura estável).
