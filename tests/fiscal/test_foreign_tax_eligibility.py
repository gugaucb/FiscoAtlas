"""Ticket 03 (roadmap-compliance) — Elegibilidade do crédito de imposto exterior.

Regras: RF-FTC-002/003/004, RF-VAL-009 (Lei 14.754/2023, art. 4º —
reciprocidade de tratamento para tributos FEDERAIS sobre a renda).
- FEDERAL + país com reciprocidade → crédito conforme regra vigente;
- STATE/LOCAL/UNKNOWN ou país sem reciprocidade → crédito 0, segregado
  no relatório como imposto não elegível.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from django.core.exceptions import ValidationError

from fiscal.engine import TaxEngine
from fiscal.models import TaxRule
from fiscal.report import ReportService
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


def _dividendo(conta, **extra):
    base = dict(
        event_type="DIVIDEND", account=conta, asset=Asset.objects.get(ticker="AAPL"),
        trade_date=date(2026, 3, 10), quantity=Decimal(100), per_share_usd=Decimal(1),
        tax_usd=Decimal(30), foreign_tax_payment_date=date(2026, 3, 10),
        date_evidence_source="BROKER_STATEMENT", country_code="US",
        jurisdiction_level="FEDERAL", tax_type="WITHHOLDING_INCOME_TAX",
    )
    base.update(extra)
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(base)


def _compute():
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        return TaxEngine(2026).compute()


def test_federal_us_gera_credito(setup):
    _dividendo(setup, jurisdiction_level="FEDERAL", tax_type="WITHHOLDING_INCOME_TAX")
    resultado = _compute()
    # bruto 100 USD × 5 = R$ 500 → limite de 15% = R$ 75; retenção R$ 150
    assert resultado["withholding_credit_brl"] == Decimal("75.00")
    assert resultado["ineligible_foreign_tax_brl"] == Decimal("0.00")


@pytest.mark.parametrize("juris", ["STATE", "LOCAL"])
def test_jurisdicao_nao_federal_credito_zero(setup, juris):
    _dividendo(setup, jurisdiction_level=juris)
    resultado = _compute()
    assert resultado["withholding_credit_brl"] == Decimal("0.00")
    # segregado como não elegível (30 USD × PTAX COMPRA 5 = R$ 150)
    assert resultado["ineligible_foreign_tax_brl"] == Decimal("150.00")


def test_jurisdicao_unknown_credito_zero_sem_julgamento(setup):
    _dividendo(setup, jurisdiction_level="UNKNOWN")
    resultado = _compute()
    assert resultado["withholding_credit_brl"] == Decimal("0.00")
    assert resultado["ineligible_foreign_tax_brl"] == Decimal("150.00")


def test_pais_sem_reciprocidade_credito_zero(setup):
    _dividendo(setup, country_code="GB", jurisdiction_level="FEDERAL")
    resultado = _compute()
    assert resultado["withholding_credit_brl"] == Decimal("0.00")
    assert resultado["ineligible_foreign_tax_brl"] == Decimal("150.00")


def test_detail_marca_elegibilidade(setup):
    _dividendo(setup, jurisdiction_level="FEDERAL")
    _dividendo(setup, jurisdiction_level="STATE")
    resultado = _compute()
    divs = [d for d in resultado["detail"] if d["kind"] == "dividend"]
    assert {d["credit_eligible"] for d in divs} == {True, False}


def test_report_segrega_ineligivel(setup):
    _dividendo(setup, jurisdiction_level="STATE")
    with mock.patch("fiscal.report.PtaxService.get_rate",
                    return_value=mock.Mock(rate=RATE, effective_date=date(2026, 12, 31))):
        report = ReportService(2026).build()
    assert report["income"]["ineligible_foreign_tax_brl"] == Decimal("150.00")
    linha = report["income"]["credit_detail"][0]
    assert linha["credit_eligible"] is False
    assert linha["credit_used_brl"] == Decimal("0.00")


def test_evento_sem_pagamento_legado_mantem_credito(setup):
    """Transição: evento antecipado à entidade ForeignTaxPayment não é punido."""
    ev = _dividendo(setup, foreign_tax_payment_date=None, confirm_same_day=True)
    ev.foreign_tax_payments.all().delete()  # simula legado
    resultado = _compute()
    assert resultado["withholding_credit_brl"] == Decimal("75.00")
