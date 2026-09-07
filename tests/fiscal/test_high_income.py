"""Ticket 10 (roadmap-compliance) — Tributação mínima de altas rendas.

Lei nº 15.270/2025 (RF-HI-001..004, CT-024/CT-025): a partir de 2026,
contribuintes com renda global anual > R$ 600.000 ficam sujeitos à
tributação mínima. A plataforma apura rendimentos NO EXTERIOR; se só esse
recorte já supera o limiar, alerta; caso contrário o teste é indeterminado
(não enxerga a renda global do contribuinte).
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from fiscal.high_income import HighIncomeService
from fiscal.models import TaxRule
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


def _dividendo_brl(ano, valor_brl, conta=None, asset=None):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="DIVIDEND", account=conta, asset=asset,
            trade_date=date(ano, 6, 1), quantity=Decimal(1),
            per_share_usd=valor_brl / Decimal(5) - Decimal(0), tax_usd=Decimal(0),
        ))


@pytest.fixture
def ambiente(residente, db):
    for ano in (2025, 2026):
        TaxRule.objects.create(
            tax_year=ano, rule_version="V2",
            brackets=[{"limit_brl": None, "rate": "0.15"}],
            confirmed=True, quote_type="VENDA", date_rule="INCOME_RECEIPT_DATE",
            effective_from=date(ano, 1, 1),
        )
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    return conta, aapl


def test_ano_anterior_a_2026_nao_aciona(ambiente):
    conta, aapl = ambiente
    _dividendo_brl(2025, Decimal(1000000), conta=conta, asset=aapl)
    resultado = HighIncomeService(2025).evaluate()
    assert resultado["status"] == "HIGH_INCOME_NOT_APPLICABLE"


def test_ct024_rendimento_menor_que_o_limiar_e_undetermined(ambiente):
    conta, aapl = ambiente
    _dividendo_brl(2026, Decimal(100000), conta=conta, asset=aapl)
    resultado = HighIncomeService(2026).evaluate()
    assert resultado["status"] == "HIGH_INCOME_TEST_UNDETERMINED"
    assert resultado["foreign_income_brl"] == Decimal(100000)
    assert resultado["message"]  # instrutiva


def test_ct025_acima_de_600_mil_excede_o_limiar(ambiente):
    conta, aapl = ambiente
    _dividendo_brl(2026, Decimal(700000), conta=conta, asset=aapl)
    resultado = HighIncomeService(2026).evaluate()
    assert resultado["status"] == "HIGH_INCOME_THRESHOLD_EXCEEDED"
    assert resultado["highlight"] is True


def test_exposto_no_relatorio(ambiente):
    from fiscal.report import ReportService
    conta, aapl = ambiente
    _dividendo_brl(2026, Decimal(700000), conta=conta, asset=aapl)
    with mock.patch("fx.service.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        report = ReportService(2026).build()
    assert report["high_income"]["status"] == "HIGH_INCOME_THRESHOLD_EXCEEDED"
