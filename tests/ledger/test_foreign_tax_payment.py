"""Ticket 01 — ForeignTaxPayment registra fatos do imposto pago no exterior.

Regras: datas de rendimento e de imposto são independentes (sem fallback
silencioso); evidência documental obrigatória; elegibilidade fiscal fica
fora deste ticket (ForeignTaxCreditEngine, ticket 03).
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from ledger.models import BrokerAccount, FinancialEvent, ForeignTaxPayment
from ledger.service import EventService

pytestmark = pytest.mark.django_db


@pytest.fixture
def conta():
    return BrokerAccount.objects.create(broker_name="Avenue", account_number="123", is_interest_bearing=True)


def _dividendo(conta, **extra):
    base = dict(
        event_type="DIVIDEND",
        account=conta,
        trade_date=date(2026, 3, 10),
        quantity=Decimal(10),
        per_share_usd=Decimal(10),
        tax_usd=Decimal(30),
        foreign_tax_payment_date=date(2026, 3, 12),
        date_evidence_source="BROKER_STATEMENT",
        country_code="US",
        jurisdiction_level="FEDERAL",
        tax_type="WITHHOLDING_INCOME_TAX",
    )
    base.update(extra)
    return EventService().record(base)


def test_retencao_com_data_propria(conta):
    ev = _dividendo(conta)
    pagamento = ev.foreign_tax_payments.get()
    assert pagamento.tax_usd == Decimal(30)
    assert pagamento.foreign_tax_payment_date == date(2026, 3, 12)
    assert pagamento.country_code == "US"
    assert pagamento.jurisdiction_level == "FEDERAL"
    assert pagamento.tax_type == "WITHHOLDING_INCOME_TAX"
    assert pagamento.capture_method == "MANUAL"
    assert pagamento.date_evidence_source == "BROKER_STATEMENT"


def test_imposto_sem_data_erro_explicito_e_nada_persistido(conta):
    with pytest.raises(ValueError, match="data de pagamento do imposto"):
        _dividendo(conta, foreign_tax_payment_date=None, confirm_same_day=False)
    assert FinancialEvent.objects.count() == 0
    assert ForeignTaxPayment.objects.count() == 0


def test_mesmo_dia_confirmado_usa_data_do_evento_e_exige_evidencia(conta):
    ev = _dividendo(
        conta,
        foreign_tax_payment_date=None,
        confirm_same_day=True,
        date_evidence_source="USER_CONFIRMED",
    )
    pagamento = ev.foreign_tax_payments.get()
    # helper de compatibilidade: hoje a data base do evento é trade_date
    assert pagamento.foreign_tax_payment_date == ev.trade_date

    with pytest.raises(ValueError, match="evidência|evidencia"):
        _dividendo(
            conta,
            foreign_tax_payment_date=None,
            confirm_same_day=True,
            date_evidence_source="UNKNOWN",
        )


def test_jurisdicao_unknown_registra_fato_sem_julgamento(conta):
    ev = _dividendo(conta, jurisdiction_level="UNKNOWN")
    pagamento = ev.foreign_tax_payments.get()
    assert pagamento.jurisdiction_level == "UNKNOWN"
    # sem campo de elegibilidade neste ticket — decisão é do CreditEngine


def test_tax_type_other_registra_fato_sem_julgamento(conta):
    ev = _dividendo(conta, tax_type="OTHER")
    assert ev.foreign_tax_payments.get().tax_type == "OTHER"


def test_sem_imposto_nao_cria_pagamento(conta):
    ev = _dividendo(conta, tax_usd=Decimal(0), per_share_usd=Decimal(13))
    assert ev.foreign_tax_payments.count() == 0


def test_cardinalidade_zero_para_n(conta):
    ev = _dividendo(conta)
    ForeignTaxPayment.objects.create(
        financial_event=ev,
        tax_usd=Decimal(5),
        foreign_tax_payment_date=date(2026, 3, 13),
        country_code="US",
        jurisdiction_level="STATE",
        tax_type="INCOME_TAX",
        capture_method="MANUAL",
        date_evidence_source="BROKER_TAX_REPORT",
    )
    assert ev.foreign_tax_payments.count() == 2


def test_tax_usd_de_pagamento_deve_ser_positivo(conta):
    with pytest.raises(ValueError):
        ForeignTaxPayment.objects.create(
            financial_event=_dividendo(conta),
            tax_usd=Decimal(0),
            foreign_tax_payment_date=date(2026, 3, 12),
            country_code="US",
            jurisdiction_level="FEDERAL",
            tax_type="WITHHOLDING_INCOME_TAX",
            capture_method="MANUAL",
            date_evidence_source="BROKER_STATEMENT",
        )


def test_atomicidade_evento_sem_pagamento_nao_persiste(conta):
    with mock.patch(
        "ledger.service.ForeignTaxPayment.objects.create",
        side_effect=ValueError("boom"),
    ):
        with pytest.raises(ValueError):
            _dividendo(conta)
    assert FinancialEvent.objects.count() == 0
    assert ForeignTaxPayment.objects.count() == 0
