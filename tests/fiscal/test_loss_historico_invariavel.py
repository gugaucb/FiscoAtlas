"""Ticket 29 (P0 do auditor) — apuração histórica de prejuízos invariável.

O prejuízo herdado por TaxEngine.compute(year) é reconstruído
historicamente (amount_brl − compensações de anos ANTERIORES ao ano
apurado), nunca pelo remaining_brl mutável do ledger — o resultado do ano
não muda porque compensações ocorreram nele ou depois dele.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from fiscal.engine import TaxEngine
from fiscal.losses import LossLedgerService
from fiscal.models import AnnualAssessment, LossRecord, TaxRule
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def rules(db):
    for ano in (2024, 2025, 2026):
        TaxRule.objects.create(
            tax_year=ano, rule_version="V2",
            brackets=[{"limit_brl": None, "rate": "0.15"}],
            confirmed=True,
            effective_from=date(ano, 1, 1), effective_until=date(ano, 12, 31),
        )


def _venda_perda(conta, asset, ano, perda_usd):
    """Compra 100@100 e vende com preço que gera perda_usd em USD."""
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="BUY", account=conta, asset=asset,
            trade_date=date(ano, 1, 5), quantity=Decimal(100),
            price_usd=Decimal(100), fee_usd=Decimal(0),
        ))
        return EventService().record(dict(
            event_type="SELL", account=conta, asset=asset,
            trade_date=date(ano, 6, 1), quantity=Decimal(100),
            price_usd=Decimal(100) - perda_usd, fee_usd=Decimal(0),
        ))


def _computa(ano):
    with mock.patch("fiscal.engine.PtaxService.get_rate",
                    return_value=mock.Mock(rate=RATE, effective_date=date(ano, 12, 31))):
        return TaxEngine(ano).compute()


def _fechar(ano):
    with mock.patch("fiscal.engine.PtaxService.get_rate",
                    return_value=mock.Mock(rate=RATE, effective_date=date(ano, 12, 31))):
        return TaxEngine(ano).save_snapshot(ano)


def _conta():
    return BrokerAccount.objects.create(broker_name="Avenue", account_number="1")


def _perda_mil_brl_2024(conta, asset):
    """Perda de R$1.000 em 2024 (US$200 × 5): compra 100@100, vende @98."""
    return _venda_perda(conta, asset, 2024, Decimal(2))  # (98−100)×100 = −200 USD ×5


# 1) invariância após fechar o próprio ano

def test_compute_invariante_apos_fechar_proprio_ano(db, residente):
    conta = _conta()
    asset = Asset.objects.create(ticker="NVDA", description="Nvidia", asset_type="FOREIGN_EQUITY")
    ev = _perda_mil_brl_2024(conta, asset)  # perda R$1.000
    TaxEngine(2024).save_snapshot(2024)  # registra a perda no ledger (fechamento 2024)
    conta25 = BrokerAccount.objects.create(broker_name="Avenue 2", account_number="2")
    _venda_perda_25 = None
    # 2025: renda tributável R$600 (ganho US$120 ×5)
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="BUY", account=conta25, asset=asset,
            trade_date=date(2025, 1, 5), quantity=Decimal(100),
            price_usd=Decimal(100), fee_usd=Decimal(0),
        ))
        EventService().record(dict(
            event_type="SELL", account=conta25, asset=asset,
            trade_date=date(2025, 6, 1), quantity=Decimal(100),
            price_usd=Decimal("101.2"), fee_usd=Decimal(0),  # ganho US$1,2/ação → R$600
        ))
    with mock.patch("fiscal.engine.PtaxService.get_rate",
                    return_value=mock.Mock(rate=RATE, effective_date=date(2025, 12, 31))):
        antes = TaxEngine(2025).compute()
    assert antes["loss_inherited_brl"] == Decimal("1000.00")
    assert antes["taxable_brl"] == Decimal("0")
    assert antes["loss_carryforward_brl"] == Decimal("400.00")

    TaxEngine(2025).save_snapshot(2025)  # fecha 2025: consome R$600

    with mock.patch("fiscal.engine.PtaxService.get_rate",
                    return_value=mock.Mock(rate=RATE, effective_date=date(2025, 12, 31))):
        depois = TaxEngine(2025).compute()
    assert depois["loss_inherited_brl"] == Decimal("1000.00")  # falha no código atual: 400
    assert depois["taxable_brl"] == Decimal("0")
    assert depois["loss_carryforward_brl"] == Decimal("400.00")


# 2) invariância após anos posteriores consumirem parte do saldo

def test_compute_invariante_com_consumos_posteriores(db, residente):
    conta = _conta()
    asset = Asset.objects.create(ticker="NVDA", description="Nvidia", asset_type="FOREIGN_EQUITY")
    _perda_mil_brl_2024(conta, asset)  # perda R$1.000 em 2024
    TaxEngine(2024).save_snapshot(2024)  # registra a perda no ledger
    for ano, ganho_brl, _s in ((2025, Decimal(600), 1), (2026, Decimal(200), 2)):
        conta_n = BrokerAccount.objects.create(
            broker_name=f"Avenue {ano}", account_number=str(ano))
        with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
            EventService().record(dict(
                event_type="BUY", account=conta_n, asset=asset,
                trade_date=date(ano, 1, 5), quantity=Decimal(100),
                price_usd=Decimal(100), fee_usd=Decimal(0),
            ))
            EventService().record(dict(
                event_type="SELL", account=conta_n, asset=asset,
                trade_date=date(ano, 6, 1), quantity=Decimal(100),
                price_usd=Decimal(100) + ganho_brl / 500, fee_usd=Decimal(0),
            ))
        TaxEngine(ano).save_snapshot(ano)

    with mock.patch("fiscal.engine.PtaxService.get_rate",
                    return_value=mock.Mock(rate=RATE, effective_date=date(2025, 12, 31))):
        r2025 = TaxEngine(2025).compute()
    assert r2025["loss_inherited_brl"] == Decimal("1000.00")  # histórico: início de 2025
    with mock.patch("fiscal.engine.PtaxService.get_rate",
                    return_value=mock.Mock(rate=RATE, effective_date=date(2026, 12, 31))):
        r2026 = TaxEngine(2026).compute()
    assert r2026["loss_inherited_brl"] == Decimal("400.00")   # 1.000 − 600 (2025)
    # saldo OPERACIONAL atual para 2027 continua 200
    assert LossLedgerService.available(2026) == Decimal("200.00")


# 3) API histórica

def test_available_at_start_of(db, residente):
    record = LossLedgerService.record_loss(2024, Decimal(1000))
    LossLedgerService.apply_compensation(2025, Decimal(600))
    LossLedgerService.apply_compensation(2026, Decimal(200))
    assert LossLedgerService.available_at_start_of(2025) == Decimal("1000.00")
    assert LossLedgerService.available_at_start_of(2026) == Decimal("400.00")
    assert LossLedgerService.available_at_start_of(2027) == Decimal("200.00")


def test_api_historica_exclui_source_event_inativo(db, residente):
    conta = _conta()
    asset = Asset.objects.create(ticker="MSFT", description="Microsoft", asset_type="FOREIGN_EQUITY")
    ev = _venda_perda(conta, asset, 2024, Decimal(2))
    ev.active = False
    ev.save(update_fields=["active"])
    assert LossLedgerService.available_at_start_of(2025) == Decimal("0.00")


# 4) ano fechado não pode ser fechado novamente

def test_ano_confirmado_nao_refecha(client, db, residente):
    from fiscal.models import AnnualAssessment as AA
    snapshot = AA.objects.create(
        year=2025, rule_version="V2", income_brl=0, loss_brl=0,
        taxable_brl=0, tax_brl=0, withholding_credit_brl=0, tax_due_brl=0,
        loss_carryforward_brl=0, detail=[], confirmed=True,
    )
    records_antes = list(LossRecord.objects.values_list("remaining_brl", flat=True))
    resp = client.post("/apuracao/2025/fechar/")
    assert resp.status_code == 302
    page = client.get("/apuracao/2025/").content.decode()
    assert "já está fechado" in page
    snapshot.refresh_from_db()
    assert snapshot.confirmed is True
    assert list(LossRecord.objects.values_list("remaining_brl", flat=True)) == records_antes


def test_interface_mostra_reabrir_ano_fechado(client, db, residente):
    from fiscal.models import AnnualAssessment as AA
    AA.objects.create(
        year=2025, rule_version="V2", income_brl=0, loss_brl=0,
        taxable_brl=0, tax_brl=0, withholding_credit_brl=0, tax_due_brl=0,
        loss_carryforward_brl=0, detail=[], confirmed=True,
    )
    page = client.get("/apuracao/2025/").content.decode()
    assert "Reabrir ano" in page
    assert "/fechar/" not in page