"""Ticket 08 (roadmap-compliance) — Ledger granular de perdas (RF-LOS-006/007).

CT-004/CT-005: cada prejuízo é rastreável até o evento de alienação e ao
ano de origem; a compensação anual segue FIFO e os saldos remanescentes
são auditáveis ano a ano.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from fiscal.engine import TaxEngine
from fiscal.models import AnnualAssessment, LossCompensation, LossRecord, TaxRule
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


def _buy_sell(conta, asset, ano, buy_price=Decimal(100), sell_price=Decimal(100),
              qty=Decimal(10), buy_dia=None, sell_dia=None):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="BUY", account=conta, asset=asset,
            trade_date=buy_dia or date(ano, 1, 5), quantity=qty,
            price_usd=buy_price, fee_usd=Decimal(0),
        ))
        return EventService().record(dict(
            event_type="SELL", account=conta, asset=asset,
            trade_date=sell_dia or date(ano, 6, 1), quantity=qty,
            price_usd=sell_price, fee_usd=Decimal(0),
        ))


def _conta(ano):
    return BrokerAccount.objects.create(broker_name="Avenue", account_number=str(ano))


@pytest.fixture
def rules(db):
    for ano in (2024, 2025, 2026):
        TaxRule.objects.create(
            tax_year=ano, rule_version="V2",
            brackets=[{"limit_brl": None, "rate": "0.15"}],
            confirmed=True, quote_type="VENDA", date_rule="INCOME_RECEIPT_DATE",
            effective_from=date(ano, 1, 1),
        )


# ------------------------------------------------- registro com origem

def test_ledger_registra_origem_do_prejuizo(db, residente, rules):
    conta = _conta(2024)
    asset = Asset.objects.create(ticker="NVDA", description="Nvidia", asset_type="FOREIGN_EQUITY")
    ev = _buy_sell(conta, asset, 2024, sell_price=Decimal(70))  # 3500 − 5000 = −1500
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        TaxEngine(2024).save_snapshot(2024)
    r = LossRecord.objects.get()
    assert r.origin_year == 2024
    assert r.amount_brl == Decimal("1500.00")
    assert r.remaining_brl == Decimal("1500.00")
    assert r.source_event_id == ev.pk


# ------------------------------------------------- CT-005 FIFO multianual

def test_ct005_fifo_multianual_compensa_e_rastreia(db, residente, rules):
    conta = _conta(2024)
    asset = Asset.objects.create(ticker="NVDA", description="Nvidia", asset_type="FOREIGN_EQUITY")
    # perda 1: 1.500 (vende @70); perda 2: 500 (vende @90)
    _buy_sell(conta, asset, 2024, sell_price=Decimal(70), sell_dia=date(2024, 5, 1))
    _buy_sell(conta, asset, 2024, sell_price=Decimal(90), sell_dia=date(2024, 7, 1),
              buy_dia=date(2024, 2, 5))
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        TaxEngine(2024).save_snapshot(2024)
    assert sum(r.remaining_brl for r in LossRecord.objects.all()) == Decimal(2000)

    # 2025: ganho de 1.000 (vende @120) → FIFO compensa do registro mais antigo
    conta25 = _conta(2025)
    _buy_sell(conta25, asset, 2025, sell_price=Decimal(120))
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        TaxEngine(2025).save_snapshot(2025)
    registros = list(LossRecord.objects.order_by("origin_year", "id"))
    assert registros[0].remaining_brl == Decimal(500)   # 1500 − 1000
    assert registros[1].remaining_brl == Decimal(500)   # intocado (FIFO)
    snapshot25 = AnnualAssessment.objects.get(year=2025)
    assert snapshot25.loss_carryforward_brl == Decimal(1000)
    assert LossCompensation.objects.filter(year=2025).count() == 1


def test_compensacao_eh_idempotente(db, residente, rules):
    conta = _conta(2024)
    asset = Asset.objects.create(ticker="NVDA", description="Nvidia", asset_type="FOREIGN_EQUITY")
    _buy_sell(conta, asset, 2024, sell_price=Decimal(70))
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        TaxEngine(2024).save_snapshot(2024)
        TaxEngine(2024).save_snapshot(2024)
    # 2024 não tem rendimento: nada a compensar; saldo intocado após refechamento
    assert LossCompensation.objects.filter(year=2024).count() == 0
    assert LossRecord.objects.get().remaining_brl == Decimal(1500)


# ------------------------------------------------- relatório discrimina origem

def test_engine_discrimina_origem_da_perda_herdada(db, residente, rules):
    conta = _conta(2024)
    asset = Asset.objects.create(ticker="NVDA", description="Nvidia", asset_type="FOREIGN_EQUITY")
    _buy_sell(conta, asset, 2024, sell_price=Decimal(70))
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        TaxEngine(2024).save_snapshot(2024)
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        resultado = TaxEngine(2025).compute()
    linhas = [d for d in resultado["detail"] if d["kind"] == "loss_carryforward"]
    assert any("2024" in (d.get("description") or "") for d in linhas)
    assert resultado["loss_inherited_brl"] == Decimal(1500)


def test_sem_registros_cai_no_scalar_do_ano_anterior(db, residente, rules):
    """Transição: dados legados (snapshot sem LossRecord) continuam compensando."""
    AnnualAssessment.objects.create(
        year=2024, rule_version="V2", income_brl=Decimal(0), loss_brl=Decimal(2000),
        taxable_brl=Decimal(0), tax_brl=Decimal(0), withholding_credit_brl=Decimal(0),
        tax_due_brl=Decimal(0), loss_carryforward_brl=Decimal(2000),
    )
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        resultado = TaxEngine(2025).compute()
    assert resultado["loss_inherited_brl"] == Decimal(2000)
