"""Auditoria-fiscal 10 — data de RECEBIMENTO como fato gerador do rendimento.

Regressão: antes, o único campo de data era trade_date — o ano fiscal e a
PTAX do rendimento vinham da data da OPERAÇÃO. Um dividendo negociado em
31/12 mas creditado em 02/01 era tributado no ano errado, com a PTAX errada.
Ganhos de alienação NÃO mudam: a data da operação é o fato gerador correto
do ganho no IRPF (não-regressão documentada).
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from fiscal.engine import TaxEngine
from fiscal.models import TaxRule
from fiscal.date_rules import TaxDateResolver
from fx.models import PtaxRate
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

PTAX_31_12 = Decimal("5.00000000")
PTAX_02_01 = Decimal("5.50000000")
PTAX_COMPRA_02_01 = Decimal("5.20000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(db, residente):
    # PTAX reais em banco (sem mock): VENDA muda de 31/12 para 02/01 —
    # qualquer resolução pela trade_date produz 5,00, pela data fiscal 5,50.
    PtaxRate.objects.create(requested_date=date(2026, 12, 31), effective_date=date(2026, 12, 31), rate=PTAX_31_12)
    PtaxRate.objects.create(requested_date=date(2027, 1, 2), effective_date=date(2027, 1, 2), rate=PTAX_02_01)
    PtaxRate.objects.create(requested_date=date(2027, 1, 2), effective_date=date(2027, 1, 2), quote_type="COMPRA", rate=PTAX_COMPRA_02_01)
    TaxRule.objects.create(
        tax_year=2027, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, effective_from=date(2027, 1, 1),
    )
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, effective_from=date(2026, 1, 1), effective_until=date(2026, 12, 31),
    )
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    return acct, asset


def test_dividendo_negociado_31_12_creditado_02_01_pertence_ao_ano_recebimento(setup):
    """Fato gerador do rendimento é o recebimento — falha no código atual,
    que tributava no ano da operação (2026)."""
    acct, asset = setup
    ev = EventService().record(dict(
        account=acct, event_type="DIVIDEND", asset=asset,
        trade_date=date(2026, 12, 31), quantity=Decimal(100),
        per_share_usd=Decimal(1), income_receipt_date=date(2027, 1, 2),
    ))
    assert ev.income_receipt_date == date(2027, 1, 2)
    assert TaxEngine(2026).compute()["income_brl"] == Decimal("0.00")
    assert TaxEngine(2027).compute()["income_brl"] == Decimal("550.00")


def test_ptax_do_rendimento_e_da_data_de_recebimento(setup):
    """PTAX VENDA do fato gerador (02/01 → 5,50), não da operação (31/12 → 5,00).
    Falha no código atual, que convertia sempre pela trade_date."""
    acct, asset = setup
    ev = EventService().record(dict(
        account=acct, event_type="DIVIDEND", asset=asset,
        trade_date=date(2026, 12, 31), quantity=Decimal(100),
        per_share_usd=Decimal(1), income_receipt_date=date(2027, 1, 2),
    ))
    assert ev.fx_rate == PTAX_02_01
    assert ev.amount_brl == Decimal("550.00000000")


def test_recebimento_default_e_a_data_da_operacao(setup):
    """Crédito no mesmo dia da operação é o caso normal — default EXPLÍCITO
    gravado no capture (o resolver nunca presume trade_date silenciosamente)."""
    acct, asset = setup
    ev = EventService().record(dict(
        account=acct, event_type="DIVIDEND", asset=asset,
        trade_date=date(2026, 6, 15), quantity=Decimal(10), per_share_usd=Decimal(1),
    ))
    assert ev.income_receipt_date == date(2026, 6, 15)


def test_imposto_pago_02_01_converte_pela_ptax_do_ano_do_pagamento(setup):
    """Imposto pago no exterior tem data própria: PTAX COMPRA de 02/01/2027
    (5,20), mesmo com o rendimento recebido naquele ano."""
    acct, asset = setup
    ev = EventService().record(dict(
        account=acct, event_type="DIVIDEND", asset=asset,
        trade_date=date(2027, 1, 2), quantity=Decimal(100),
        per_share_usd=Decimal(10), tax_usd=Decimal(30),
        foreign_tax_payment_date=date(2027, 1, 2),
        date_evidence_source="BROKER_STATEMENT", country_code="US",
        jurisdiction_level="FEDERAL", tax_type="WITHHOLDING_INCOME_TAX",
    ))
    result = TaxEngine(2027).compute()
    d = next(x for x in result["detail"] if x.get("event") == ev)
    assert d["fx_tax"] == PTAX_COMPRA_02_01
    # wh = 30 USD × 5,20 = 156,00
    assert d["withholding_brl"] == Decimal("156.00")


def test_ganho_de_alienacao_mantem_a_data_da_operacao(setup):
    """NÃO-REGRESSÃO: a trade_date é o fato gerador correto do ganho no IRPF.
    Venda em 31/12/2026 permanece no ano 2026 (mudar isso seria errado)."""
    acct, asset = setup
    with mock.patch.object(EventService, "_ptax_rate", return_value=Decimal("5.00000000")):
        EventService().record(dict(
            account=acct, event_type="APORTE", trade_date=date(2026, 1, 2), amount_usd=Decimal(20000),
        ))
        EventService().record(dict(
            account=acct, event_type="BUY", asset=asset, trade_date=date(2026, 1, 3),
            quantity=Decimal(100), price_usd=Decimal(100),
        ))
    EventService().record(dict(
        account=acct, event_type="SELL", asset=asset, trade_date=date(2026, 12, 31),
        quantity=Decimal(100), price_usd=Decimal(110),
    ))
    assert TaxEngine(2026).compute()["income_brl"] == Decimal("5000.00")
    assert TaxEngine(2027).compute()["income_brl"] == Decimal("0.00")


def test_resolver_exige_data_de_recebimento_sem_fallback(setup):
    """Rendimento legado sem income_receipt_date: erro explícito, nunca
    fallback silencioso para a trade_date."""
    acct, asset = setup
    ev = EventService().record(dict(
        account=acct, event_type="DIVIDEND", asset=asset,
        trade_date=date(2026, 6, 15), quantity=Decimal(10), per_share_usd=Decimal(1),
    ))
    ev.income_receipt_date = None
    ev.save(update_fields=["income_receipt_date"])
    from django.core.exceptions import ValidationError
    with pytest.raises(ValidationError, match="sem data de recebimento"):
        TaxEngine(2026).compute()
    with pytest.raises(ValueError, match="income_receipt_date"):
        TaxDateResolver().resolve(event=ev, date_rule="INCOME_RECEIPT_DATE")