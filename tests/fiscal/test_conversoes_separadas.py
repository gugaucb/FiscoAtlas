"""Ticket 03 — conversões independentes: rendimento VENDA, imposto COMPRA.

Cenário: dividendo 10/03/2026 US$100 (gross), imposto pago 12/03/2026 US$30.
PTAX VENDA 10/03 = 5,00; PTAX COMPRA 12/03 = 4,90 (diferentes de propósito).
Engine, relatório e memória devem converter o imposto pela COMPRA.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from fiscal.engine import TaxEngine
from fiscal.models import TaxRule
from fiscal.memoria import build_memoria
from fiscal.report import ReportService
from fx.models import PtaxRate
from ledger.models import BrokerAccount, FinancialEvent, ForeignTaxPayment
from ledger.position import PositionService
from ledger.service import EventService

pytestmark = pytest.mark.django_db

SELL_10_03 = Decimal("5.00")  # VENDA 10/03 — usada no rendimento
BUY_12_03 = Decimal("4.80")   # COMPRA 12/03 — usada no imposto
RATE = Decimal("5.00")


@pytest.fixture(autouse=True)
def regra_2026():
    from fiscal.management.commands.seed_tax_rules import BRACKETS
    TaxRule.objects.create(
        tax_year=2026, rule_version="TEST", brackets=BRACKETS,
        quote_type="VENDA", date_rule="INCOME_RECEIPT_DATE", confirmed=True,
        effective_from=date(2026, 1, 1),
    )


@pytest.fixture
def dividendo_12_03():
    from ledger.models import Asset
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="STOCK")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="BUY", account=conta, asset=asset, trade_date=date(2026, 1, 5),
            quantity=Decimal(10), price_usd=Decimal(100), fee_usd=Decimal(0),
        ))
        ev = EventService().record(dict(
            event_type="DIVIDEND", account=conta, asset=asset, trade_date=date(2026, 3, 10),
            quantity=Decimal(10), per_share_usd=Decimal(10), tax_usd=Decimal(30),
            foreign_tax_payment_date=date(2026, 3, 12),
            date_evidence_source="BROKER_STATEMENT", country_code="US",
            jurisdiction_level="FEDERAL", tax_type="WITHHOLDING_INCOME_TAX",
        ))
    pagamento = ev.foreign_tax_payments.get()
    # preço da cotação por (data, tipo): VENDA 10/03 = 5,00; COMPRA 12/03 = 4,80
    def fake_get_rate(self, requested, quote_type="VENDA"):
        fake = PtaxRate(requested_date=requested, effective_date=requested,
                        quote_type=quote_type,
                        rate=BUY_12_03 if quote_type == "COMPRA" else RATE)
        return fake
    with mock.patch("fx.service.PtaxService.get_rate", autospec=True, side_effect=fake_get_rate):
        yield ev, pagamento, fake_get_rate


def _registrar_ptax_fixtures(ev):
    pass  # cotações são mockadas


def test_engine_converte_imposto_pela_compra(dividendo_12_03):
    ev, pagamento, _ = dividendo_12_03
    result = TaxEngine(2026).compute()
    # rendimento: US$100 × 5,00 (VENDA 10/03) = 500
    # imposto: US$30 × 4,80 (COMPRA 12/03) = 144
    d = next(x for x in result["detail"] if x["event"] and x["event"].id == ev.id)
    assert d["gross_brl"] == Decimal("500.00")
    assert d["withholding_brl"] == Decimal("144.00")


def test_memoria_usa_compra_para_ir_eua(dividendo_12_03):
    ev, pagamento, _ = dividendo_12_03
    memoria = build_memoria(2026)
    linha = next(
        r for a in memoria["assets"] for r in a["rows"]
        if r["kind"] == "DIVIDENDO" and r["event"].id == ev.id
    )
    assert linha["gross_brl"] == Decimal("500.00")
    assert linha["ir_eua_brl"] == Decimal("144.00")
    # rastreabilidade: cotações distintas registradas na memória
    assert linha["income_fx_quote"] == "VENDA"
    assert linha["ir_eua_fx_quote"] == "COMPRA"
    assert linha["ir_eua_fx_date"] == date(2026, 3, 12)


def test_report_usa_compra_para_withholding(dividendo_12_03):
    ev, pagamento, fake = dividendo_12_03
    report = ReportService(2026).build()
    asset_row = report["assets"][0]
    # dividends_brl = 100×5,00 = 500; withholding = 30×4,80 = 144
    assert asset_row["dividends_brl"] == Decimal("500.00")
    assert asset_row["withholding_brl"] == Decimal("144.00")
    credit = report["income"]["credit_detail"][0]
    assert credit["withholding_brl"] == Decimal("144.00")
    # rastreabilidade no relatório: as duas cotações discriminadas
    assert credit["fx_income"] == Decimal("5.00")
    assert credit["fx_tax"] == Decimal("4.80")
    assert credit["tax_payment_date"] == date(2026, 3, 12)
