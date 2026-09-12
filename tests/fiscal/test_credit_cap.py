"""Achado P0 do auditor — crédito exterior limitado ao IR devido.

O crédito potencial (limite de 15% por rendimento) é calculado por
evento ANTES da compensação de prejuízos; o EFETIVAMENTE utilizado não
pode exceder o IR brasileiro devido do ano. Sem o teto, o relatório
afirmava utilizar crédito maior que o imposto disponível
(credit_used_total <= tax_brl como invariante).
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from fiscal.engine import TaxEngine
from fiscal.losses import LossLedgerService
from fiscal.models import TaxRule
from ledger.models import Asset, BrokerAccount
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
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="1", is_interest_bearing=True)
    Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    return conta


def _dividendo_bruto_1000(conta):
    """Dividendo bruto R$ 1.000 (200 USD × 5) com retenção elegível R$ 150
    (30 USD × 5) — dentro do limite de 15% (150)."""
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="DIVIDEND", account=conta, asset=Asset.objects.get(ticker="AAPL"),
            trade_date=date(2026, 3, 10), quantity=Decimal(200), per_share_usd=Decimal(1),
            tax_usd=Decimal(30), foreign_tax_payment_date=date(2026, 3, 10),
            date_evidence_source="BROKER_STATEMENT", country_code="US",
            jurisdiction_level="FEDERAL", tax_type="WITHHOLDING_INCOME_TAX",
            recoverability_status="NON_RECOVERABLE",
        ))


def _compute():
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        return TaxEngine(2026).compute()


def test_credito_utilizado_limitado_ao_ir_devido(setup):
    """Cenário do auditor: bruto 1.000, retenção 150, prejuízos 900 →
    base 100, IR 15. Utilizado TEM QUE ser 15 (não 150); não aproveitado 135."""
    _dividendo_bruto_1000(setup)
    LossLedgerService.record_loss(2025, Decimal(900))  # manual/legado, sem source_event
    r = _compute()
    assert r["income_brl"] == Decimal("1000.00")
    assert r["tax_brl"] == Decimal("15.00")
    assert r["credit_potential_brl"] == Decimal("150.00")
    assert r["withholding_credit_brl"] == Decimal("15.00")   # utilizado = IR devido
    assert r["credit_unused_brl"] == Decimal("135.00")
    assert r["tax_due_brl"] == Decimal("0.00")
    assert r["withholding_credit_brl"] <= r["tax_brl"]  # invariante


def test_sem_prejuizo_credito_integral_quando_dentro_do_limite(setup):
    """Sem prejuízos, IR devido (150) >= potencial (150) → utilizado integral."""
    _dividendo_bruto_1000(setup)
    r = _compute()
    assert r["tax_brl"] == Decimal("150.00")
    assert r["credit_potential_brl"] == Decimal("150.00")
    assert r["withholding_credit_brl"] == Decimal("150.00")
    assert r["credit_unused_brl"] == Decimal("0.00")
    assert r["tax_due_brl"] == Decimal("0.00")


def test_prejuizo_parcial_reduz_utilizado_proporcionalmente(setup):
    """Prejuízo 600 → base 400 → IR 60 → utilizado 60, não aproveitado 90."""
    _dividendo_bruto_1000(setup)
    LossLedgerService.record_loss(2025, Decimal(600))
    r = _compute()
    assert r["tax_brl"] == Decimal("60.00")
    assert r["withholding_credit_brl"] == Decimal("60.00")
    assert r["credit_unused_brl"] == Decimal("90.00")


def test_relatorio_distingue_potencial_utilizado_nao_aproveitado(setup):
    from fx.service import PtaxService
    from fiscal.report import ReportService
    _dividendo_bruto_1000(setup)
    LossLedgerService.record_loss(2025, Decimal(900))
    with mock.patch.object(PtaxService, "get_rate") as get_rate:
        get_rate.return_value = mock.Mock(rate=RATE, effective_date=date(2026, 12, 31))
        report = ReportService(2026).build()
    inc = report["income"]
    assert inc["credit_potential_brl"] == Decimal("150.00")
    assert inc["withholding_credit_brl"] == Decimal("15.00")
    assert inc["credit_unused_brl"] == Decimal("135.00")
    linha = report["income"]["credit_detail"][0]
    assert linha["credit_used_brl"] == Decimal("15.00")
    assert linha["credit_unused_brl"] == Decimal("135.00")  # elegível 150 − usado 15