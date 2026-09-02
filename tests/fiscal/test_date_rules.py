"""Ticket 02 — date_rule + TaxDateResolver: data fiscal e tipo de PTAX por componente.

Regras (Lei 14.754/2023, art. 15; art. 4º §2º + IN RFB 2.180/2024):
- rendimento/operaciones → PTAX VENDA na data do fato gerador;
- imposto pago no exterior → PTAX COMPRA na data do pagamento do imposto.
BUY/SELL da operação NÃO implicam BCB_SELL/BCB_BUY da cotação.
"""
from datetime import date
from decimal import Decimal

import pytest

from fiscal.date_rules import COMPONENT_RULES, TaxDateResolver
from fiscal.models import TaxRule
from ledger.models import BrokerAccount, FinancialEvent
from ledger.service import EventService

pytestmark = pytest.mark.django_db


@pytest.fixture
def dividendo_com_imposto():
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    ev = EventService().record(dict(
        event_type="DIVIDEND", account=conta, trade_date=date(2026, 3, 10),
        quantity=Decimal(10), per_share_usd=Decimal(10), tax_usd=Decimal(30),
        foreign_tax_payment_date=date(2026, 3, 12),
        date_evidence_source="BROKER_STATEMENT", country_code="US",
        jurisdiction_level="FEDERAL", tax_type="WITHHOLDING_INCOME_TAX",
    ))
    return ev, ev.foreign_tax_payments.get()


def test_rendimento_sell_na_data_do_rendimento_e_imposto_buy_na_data_do_pagamento(dividendo_com_imposto):
    ev, pagamento = dividendo_com_imposto

    data, quote = TaxDateResolver().resolve_ptax_request("INCOME", ev)
    assert (data, quote) == (date(2026, 3, 10), "VENDA")

    data, quote = TaxDateResolver().resolve_ptax_request("FOREIGN_TAX", ev, pagamento)
    assert (data, quote) == (date(2026, 3, 12), "COMPRA")


def test_datas_iguais_cotacoes_diferentes():
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="2")
    ev = EventService().record(dict(
        event_type="DIVIDEND", account=conta, trade_date=date(2026, 3, 10),
        quantity=Decimal(10), per_share_usd=Decimal(10), tax_usd=Decimal(30),
        foreign_tax_payment_date=date(2026, 3, 10),
        date_evidence_source="BROKER_STATEMENT", country_code="US",
        jurisdiction_level="FEDERAL", tax_type="WITHHOLDING_INCOME_TAX",
    ))
    pagamento = ev.foreign_tax_payments.get()

    # mesma data, cotações distintas
    assert TaxDateResolver().resolve_ptax_request("INCOME", ev) == (date(2026, 3, 10), "VENDA")
    assert TaxDateResolver().resolve_ptax_request("FOREIGN_TAX", ev, pagamento) == (date(2026, 3, 10), "COMPRA")


def test_imposto_sem_pagamento_erro():
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="3")
    ev = FinancialEvent.objects.create(event_type="DIVIDEND", account=conta, trade_date=date(2026, 3, 10), amount_usd=Decimal(100))
    with pytest.raises(ValueError, match="ForeignTaxPayment"):
        TaxDateResolver().resolve_ptax_request("FOREIGN_TAX", ev)


def test_tabela_de_componentes_conforme_lei():
    assert COMPONENT_RULES["ACQUISITION"] == ("ACQUISITION_DATE", "VENDA")
    assert COMPONENT_RULES["DISPOSAL"] == ("DISPOSAL_DATE", "VENDA")
    assert COMPONENT_RULES["INCOME"] == ("INCOME_RECEIPT_DATE", "VENDA")
    assert COMPONENT_RULES["FOREIGN_TAX"] == ("FOREIGN_TAX_PAYMENT_DATE", "COMPRA")


def test_resolve_datas_por_regra(dividendo_com_imposto):
    ev, pagamento = dividendo_com_imposto
    resolver = TaxDateResolver()
    assert resolver.resolve(event=ev, date_rule="ACQUISITION_DATE") == date(2026, 3, 10)
    assert resolver.resolve(event=ev, date_rule="DISPOSAL_DATE") == date(2026, 3, 10)
    assert resolver.resolve(event=ev, date_rule="INCOME_RECEIPT_DATE") == date(2026, 3, 10)
    assert resolver.resolve(event=ev, pagamento=pagamento, date_rule="FOREIGN_TAX_PAYMENT_DATE") == date(2026, 3, 12)


def test_taxrule_tem_date_rule():
    regra = TaxRule.objects.create(
        tax_year=2026, rule_version="TEST", brackets=[{"limit_brl": None, "rate": "0.15"}],
        quote_type="VENDA", date_rule="INCOME_RECEIPT_DATE", effective_from=date(2026, 1, 1),
    )
    assert regra.date_rule == "INCOME_RECEIPT_DATE"


def test_seed_grava_date_rule():
    from django.core.management import call_command

    call_command("seed_tax_rules", verbosity=0)
    v2 = TaxRule.objects.get(tax_year=2026, rule_version="V2")
    assert v2.date_rule == "INCOME_RECEIPT_DATE"
    assert v2.quote_type == "VENDA"
