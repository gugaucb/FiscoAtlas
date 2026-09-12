"""Ticket 28 (P0 do auditor) — sincronização completa do LossRecord.

O resultado fiscal ATUAL da alienação manda: compute() fica read-only e a
gravação/sincronização do Loss Ledger acontece no fechamento — criar perda
nova, atualizar valor mudado, remover perda que virou lucro. Com
compensação registrada, bloquear pedindo reabertura em cascata (ticket 26).
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from django.core.exceptions import ValidationError

from fiscal.engine import TaxEngine
from fiscal.losses import LossLedgerService
from fiscal.models import AnnualAssessment, LossRecord, TaxRule
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


def _rules(ano):
    TaxRule.objects.create(
        tax_year=ano, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True,
        effective_from=date(ano, 1, 1), effective_until=date(ano, 12, 31),
    )


@pytest.fixture(autouse=True)
def rules(db):
    for ano in (2024, 2025):
        _rules(ano)


def _compra(conta, asset, dia, price):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(dict(
            event_type="BUY", account=conta, asset=asset, trade_date=dia,
            quantity=Decimal(100), price_usd=price, fee_usd=Decimal(0),
        ))


def _venda(conta, asset, dia, price):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(dict(
            event_type="SELL", account=conta, asset=asset, trade_date=dia,
            quantity=Decimal(100), price_usd=price, fee_usd=Decimal(0),
        ))


def _conta():
    return BrokerAccount.objects.create(broker_name="Avenue", account_number="1")


def _fechar(ano):
    with mock.patch("fiscal.engine.PtaxService.get_rate",
                    return_value=mock.Mock(rate=RATE, effective_date=date(ano, 12, 31))):
        return TaxEngine(ano).save_snapshot(ano)


# ------------------------------------------------------------- read-only

def test_compute_nao_grava_no_ledger(db, residente):
    """Apenas CALCULAR (relatório, PDF, /apuracao/) não pode modificar o
    banco — comput() era read-write (record_loss no meio do cálculo)."""
    conta = _conta()
    asset = Asset.objects.create(ticker="NVDA", description="Nvidia", asset_type="FOREIGN_EQUITY")
    _compra(conta, asset, date(2024, 1, 5), Decimal(100))
    _venda(conta, asset, date(2024, 6, 1), Decimal(70))  # perda 3.000
    with mock.patch("fiscal.engine.PtaxService.get_rate",
                    return_value=mock.Mock(rate=RATE, effective_date=date(2024, 12, 31))):
        TaxEngine(2024).compute()
    assert LossRecord.objects.count() == 0  # falha no código atual: criava no compute


# ------------------------------------------------------- sincronização

def test_fechamento_cria_e_atualiza_perda(db, residente):
    """Perda nova → cria; custo-base corrigido (perda R$15.000 → R$10.000)
    → atualiza amount/remaining no refechamento. A perda é em BRL: US$300
    × PTAX 5."""
    conta = _conta()
    asset = Asset.objects.create(ticker="NVDA", description="Nvidia", asset_type="FOREIGN_EQUITY")
    _compra(conta, asset, date(2024, 1, 5), Decimal(100))
    _venda(conta, asset, date(2024, 6, 1), Decimal(70))  # perda US$300 → R$1.500... ×100 qty
    _fechar(2024)
    record = LossRecord.objects.get()
    assert record.amount_brl == Decimal("15000.00")  # (70−100)×100×5

    # correção do custo-base: preço 90 → perda passa a R$10.000 (mesma venda)
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
        event_type="BUY", account=conta, asset=asset,
        trade_date=date(2024, 1, 5), quantity=Decimal(100),
        price_usd=Decimal(90), fee_usd=Decimal(0), corrects=conta.events.get(event_type="BUY"),
    ))
    _fechar(2024)
    record.refresh_from_db()
    assert record.amount_brl == Decimal("10000.00")
    assert record.remaining_brl == Decimal("10000.00")
    assert LossLedgerService.available(2024) == Decimal("10000.00")


def test_perda_vira_lucro_remove_registro(db, residente):
    """Correção do custo-base transforma a perda em lucro → o LossRecord
    sai do ledger no refechamento (sem fallback silencioso)."""
    conta = _conta()
    asset = Asset.objects.create(ticker="NVDA", description="Nvidia", asset_type="FOREIGN_EQUITY")
    _compra(conta, asset, date(2024, 1, 5), Decimal(100))
    _venda(conta, asset, date(2024, 6, 1), Decimal(70))  # perda R$15.000
    _fechar(2024)
    EventService().record(dict(
        event_type="BUY", account=conta, asset=asset,
        trade_date=date(2024, 1, 5), quantity=Decimal(100),
        price_usd=Decimal(50), fee_usd=Decimal(0),
        corrects=conta.events.get(event_type="BUY"),
    ))
    _fechar(2024)
    assert LossRecord.objects.count() == 0
    assert LossLedgerService.available(2024) == Decimal("0.00")


def test_perda_alterada_com_compensacao_bloqueia(db, residente):
    """Perda R$7.500 compensada em 2025 (fechado); correção do custo-base
    do BUY muda o resultado da MESMA venda de 2024 → NÃO alterar
    silenciosamente: bloqueia pedindo reabertura em cascata (ticket 26
    devolve as compensações)."""
    conta = _conta()
    asset = Asset.objects.create(ticker="NVDA", description="Nvidia", asset_type="FOREIGN_EQUITY")
    _compra(conta, asset, date(2024, 1, 5), Decimal(100))
    _venda(conta, asset, date(2024, 6, 1), Decimal(85))  # perda US$150 → R$7.500
    _fechar(2024)
    record = LossRecord.objects.get()
    LossLedgerService.apply_compensation(2025, Decimal(7500))  # consome tudo
    AnnualAssessment.objects.create(
        year=2025, rule_version="V2", income_brl=7500, loss_brl=0,
        taxable_brl=0, tax_brl=0, withholding_credit_brl=0, tax_due_brl=0,
        loss_carryforward_brl=0, detail=[], confirmed=True,
    )
    EventService().record(dict(
        event_type="BUY", account=conta, asset=asset,
        trade_date=date(2024, 1, 5), quantity=Decimal(100),
        price_usd=Decimal(90), fee_usd=Decimal(0),
        corrects=conta.events.filter(event_type="BUY", active=True).first(),
    ))
    # refechar 2024 exige reabertura: a perda antiga já foi consumida em 2025
    with pytest.raises(ValidationError, match="Reabra|reabra|cascata"):
        _fechar(2024)