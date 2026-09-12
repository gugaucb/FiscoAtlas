"""Ticket 06 (auditoria-fiscal) — titularidade aplicada ao CÁLCULO.

Antes: TaxEngine tributava o valor integral e o relatório aplicava a
proporção só na exibição. Agora OwnershipService decide o fator do
contribuinte e dividendos, ganhos, perdas e crédito passam por ele.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from fiscal.engine import TaxEngine
from fiscal.models import TaxRule
from ledger.models import Asset, BrokerAccount, FinancialEvent, OpeningPosition
from ledger.ownership import OwnershipService
from ledger.position import PositionService
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(residente, db):
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, quote_type="VENDA", date_rule="INCOME_RECEIPT_DATE",
        effective_from=date(2026, 1, 1),
    )
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    conta = BrokerAccount.objects.create(
        broker_name="Avenue", account_number="1", is_interest_bearing=True,
        ownership_type="JOINT", ownership_share=Decimal("50.00"),
    )
    return conta, asset


def _dividendo(conta, asset, **extra):
    base = dict(
        event_type="DIVIDEND", account=conta, asset=asset,
        trade_date=date(2026, 3, 10), quantity=Decimal(100), per_share_usd=Decimal(1),
        date_evidence_source="BROKER_STATEMENT", country_code="US",
        jurisdiction_level="FEDERAL", tax_type="WITHHOLDING_INCOME_TAX",
        recoverability_status="NON_RECOVERABLE",
        foreign_tax_payment_date=date(2026, 3, 10),
    )
    base.update(extra)
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(base)


def _compute():
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        return TaxEngine(2026).compute()


def test_servico_central_fator(setup):
    conta, _ = setup
    assert OwnershipService.taxpayer_share_factor(conta) == Decimal("0.5")
    conta.ownership_share = Decimal("100.00")
    assert OwnershipService.taxpayer_share_factor(conta) == Decimal(1)
    conta.ownership_share = Decimal("0.00")
    assert OwnershipService.taxpayer_share_factor(conta) == Decimal(0)


def test_modelo_permite_zero_porcento_explicito(db, residente):
    """0% é decisão EXPLÍCITA do usuário (conta de terceiros) — a faixa do
    modelo passa a aceitar 0; nunca um default silencioso."""
    conta = BrokerAccount(
        broker_name="Terceiros", account_number="9",
        ownership_type="THIRD_PARTY", ownership_share=Decimal("0.00"),
    )
    conta.full_clean()  # não levanta
    conta.save()
    assert OwnershipService.taxpayer_share_factor(conta) == Decimal(0)


def test_dividendo_50_porcento_base_e_ir_atribuidos(setup):
    """Teste obrigatório do auditor: conta 50%, dividendo bruto R$ 10.000
    → base atribuída R$ 5.000, IR R$ 750 (não R$ 1.500)."""
    conta, asset = setup
    # 2000 ações × US$ 1 × PTAX 5 = R$ 10.000 bruto (sem retenção)
    _dividendo(conta, asset, quantity=Decimal(2000), per_share_usd=Decimal(1))
    resultado = _compute()
    assert resultado["income_brl"] == Decimal("5000.00")
    assert resultado["tax_brl"] == Decimal("750.00")
    assert resultado["tax_due_brl"] == Decimal("750.00")


def test_ganho_e_perda_50_porcento(setup):
    conta, asset = setup
    OpeningPosition.objects.create(
        account=conta, asset=asset, reference_date=date(2025, 12, 31),
        quantity=Decimal(100), total_cost_brl=Decimal("20000.00"),
    )
    # venda de 50 ações: custo médio R$ 200 → custo baixado R$ 10.000;
    # venda US$ 3.000 × 5 = R$ 15.000 → ganho integral R$ 5.000 → 50% = R$ 2.500
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="SELL", account=conta, asset=asset,
            trade_date=date(2026, 6, 1), quantity=Decimal(50),
            price_usd=Decimal(60),
        ))
    resultado = _compute()
    assert resultado["income_brl"] == Decimal("2500.00")
    assert resultado["tax_brl"] == Decimal("375.00")


def test_credito_exterior_50_porcento(setup):
    """Retenção e limite do crédito ficam na parcela do contribuinte."""
    conta, asset = setup
    # bruto do titular: 100 USD × 5 × 50% = R$ 250; retenção: 30 × 5 × 50% = R$ 75
    _dividendo(conta, asset, tax_usd=Decimal(30))
    resultado = _compute()
    assert resultado["income_brl"] == Decimal("250.00")
    # limite de 15% do bruto = R$ 37,50 — crédito usa a parcela atribuída
    assert resultado["withholding_credit_brl"] == Decimal("37.50")
    assert resultado["ineligible_foreign_tax_brl"] == Decimal("0.00")


def test_conta_terceiros_zero_rendimento(setup):
    conta, asset = setup
    conta.ownership_share = Decimal("0.00")
    conta.save()
    _dividendo(conta, asset, quantity=Decimal(2000), per_share_usd=Decimal(1))
    resultado = _compute()
    assert resultado["income_brl"] == Decimal("0.00")
    assert resultado["tax_brl"] == Decimal("0.00")
