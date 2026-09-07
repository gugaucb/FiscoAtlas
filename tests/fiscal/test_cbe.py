"""Ticket 07 (roadmap-compliance) — CBE / Banco Central (RF-CBE-001..007).

Res. BCB nº 278/2022: residente com capitais no exterior ≥ US$ 1.000.000 em
31/12 deve entregar CBE anual; ≥ US$ 100.000.000, obrigação trimestral.
Abaixo do limite: CBE_UNDETERMINED salvo declaração formal de completude.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from fiscal.cbe import CbeService
from fiscal.models import Profile, TaxRule
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def ambiente(residente, db):
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, quote_type="VENDA", date_rule="INCOME_RECEIPT_DATE",
        effective_from=date(2026, 1, 1),
    )
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    return conta


def _compra(conta, asset, qty, price, dia=date(2026, 1, 5)):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="BUY", account=conta, asset=asset, trade_date=dia,
            quantity=qty, price_usd=price, fee_usd=Decimal(0),
        ))


def _aporte(conta, amount, dia=date(2026, 1, 5)):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="APORTE", account=conta, trade_date=dia, amount_usd=amount,
        ))


def test_ct019_abaixo_do_limite_sem_completude_e_undetermined(ambiente):
    conta = ambiente
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    _aporte(conta, Decimal("199999.80"))
    _compra(conta, aapl, Decimal(100), Decimal("150"))  # US$15.000
    # total US$ 214.999,80 < 1M e sem declaração de completude → indeterminado
    resultado = CbeService(2026).evaluate()
    assert resultado["status"] == "CBE_UNDETERMINED"
    assert resultado["total_usd"] == Decimal("214999.80")


def test_abaixo_do_limite_com_completude_e_not_required(ambiente):
    conta = ambiente
    _aporte(conta, Decimal("199999.80"))
    Profile.objects.update(external_assets_declared_complete=True)
    resultado = CbeService(2026).evaluate()
    assert resultado["status"] == "CBE_NOT_REQUIRED"


def test_ct020_um_milhao_exige_cbe_anual(ambiente):
    conta = ambiente
    _aporte(conta, Decimal(1000000))
    resultado = CbeService(2026).evaluate()
    assert resultado["status"] == "CBE_REQUIRED"
    assert resultado["quarterly"] is False


def test_cem_milhoes_exige_cbe_trimestral(ambiente):
    conta = ambiente
    _aporte(conta, Decimal(100000000))
    resultado = CbeService(2026).evaluate()
    assert resultado["status"] == "CBE_REQUIRED"
    assert resultado["quarterly"] is True


def test_patrimonio_em_31_12_desconsidera_eventos_do_ano_seguinte(ambiente):
    conta = ambiente
    _aporte(conta, Decimal(2000000), dia=date(2026, 12, 31))
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="APORTE", account=conta, trade_date=date(2027, 1, 2),
            amount_usd=Decimal(5000000),
        ))
    resultado = CbeService(2026).evaluate()
    assert resultado["total_usd"] == Decimal(2000000)


def test_saldo_negativo_de_caixa_subtrai(ambiente):
    conta = ambiente
    _aporte(conta, Decimal(1000000))
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="WITHDRAWAL", account=conta, trade_date=date(2026, 6, 1),
            amount_usd=Decimal(100),
        ))
    resultado = CbeService(2026).evaluate()
    assert resultado["total_usd"] == Decimal("999900.00")
    assert resultado["status"] == "CBE_UNDETERMINED"


def test_cbe_aparece_no_relatorio(ambiente):
    from fiscal.report import ReportService
    conta = ambiente
    _aporte(conta, Decimal(1000000))
    with mock.patch("fx.service.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        report = ReportService(2026).build()
    assert report["cbe"]["status"] == "CBE_REQUIRED"
