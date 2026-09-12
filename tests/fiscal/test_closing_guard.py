"""Ticket 25 — guarda de ano fechado (auditor, P0).

Existindo AnnualAssessment(year=X, confirmed=True), nenhuma operação que
altere fatos fiscais de X ocorre até a reabertura explícita. O ano fiscal
segue a MESMA semântica do engine: SELL/CASH_IN_LIEU/demais → trade_date;
DIVIDEND/JUROS → income_receipt_date. Correção valida os DOIS anos
(original e corrigido); ForeignTaxPayment pertence ao ano do rendimento.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from django.core.exceptions import ValidationError

from fiscal.models import AnnualAssessment
from fx.service import PtaxService
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")


@pytest.fixture
def conta(db):
    return BrokerAccount.objects.create(broker_name="Avenue", account_number="1")


@pytest.fixture
def aapl(db):
    return Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")


def ano_fechado(year: int):
    AnnualAssessment.objects.create(
        year=year, rule_version="V2", income_brl=0, loss_brl=0, taxable_brl=0,
        tax_brl=0, withholding_credit_brl=0, tax_due_brl=0,
        loss_carryforward_brl=0, confirmed=True,
    )


@pytest.mark.django_db
def test_record_bloqueia_ano_fechado(conta, aapl, residente):
    ano_fechado(2026)
    with pytest.raises(ValidationError, match="reabrir|Reabra|fechado"):
        with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
            EventService().record(dict(
                account=conta, event_type="APORTE",
                trade_date=date(2026, 6, 1), amount_usd=Decimal(1000),
            ))


@pytest.mark.django_db
def test_snapshot_nao_confirmado_nao_bloqueia(conta, residente):
    """Snapshot existente mas NÃO confirmado (fechamento em andamento) não
    congela o ano."""
    AnnualAssessment.objects.create(
        year=2026, rule_version="V2", income_brl=0, loss_brl=0, taxable_brl=0,
        tax_brl=0, withholding_credit_brl=0, tax_due_brl=0,
        loss_carryforward_brl=0, confirmed=False,
    )
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        ev = EventService().record(dict(
            account=conta, event_type="APORTE",
            trade_date=date(2026, 6, 1), amount_usd=Decimal(1000),
        ))
    assert ev.pk


@pytest.mark.django_db
def test_rendimento_guarda_pela_data_de_recebimento(conta, aapl, residente):
    """DIVIDEND operado em 2026 mas recebido em 2027 pertence fiscalmente a
    2027 — 2026 fechado não bloqueia; 2027 fechado bloqueia."""
    ano_fechado(2026)
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        ev = EventService().record(dict(
            account=conta, event_type="DIVIDEND", asset=aapl,
            trade_date=date(2026, 12, 30), quantity=Decimal(10),
            per_share_usd=Decimal(1), income_receipt_date=date(2027, 1, 2),
            foreign_tax_state="NO_WITHHOLDING",
        ))
    assert ev.income_receipt_date == date(2027, 1, 2)


@pytest.mark.django_db
def test_correcao_valida_os_dois_anos_fiscais(conta, aapl, residente):
    """Corrigir evento fiscalmente em 2026 (fechado) movendo o fato para
    2027 NÃO pode simplesmente passar: a correção altera a história de 2026."""
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        original = EventService().record(dict(
            account=conta, event_type="APORTE",
            trade_date=date(2026, 6, 1), amount_usd=Decimal(1000),
        ))
    ano_fechado(2026)
    with pytest.raises(ValidationError, match="fechado"):
        with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
            EventService().record(dict(
                account=conta, event_type="APORTE",
                trade_date=date(2027, 1, 5), amount_usd=Decimal(1000),
                corrects=original,
            ))


@pytest.mark.django_db
def test_desativar_evento_bloqueia_ano_fechado(conta, residente):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        ev = EventService().record(dict(
            account=conta, event_type="APORTE",
            trade_date=date(2026, 6, 1), amount_usd=Decimal(1000),
        ))
    ano_fechado(2026)
    ev.active = False
    with pytest.raises(ValidationError, match="fechado"):
        ev.save(update_fields=["active"])


@pytest.mark.django_db
def test_editar_imposto_exterior_guarda_pelo_ano_do_rendimento(conta, aapl, residente):
    """Imposto pago 02/01/2027 de rendimento recebido 31/12/2026 pertence
    fiscalmente a 2026 — editar com 2026 fechado bloqueia."""
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        ev = EventService().record(dict(
            account=conta, event_type="DIVIDEND", asset=aapl,
            trade_date=date(2026, 12, 24), quantity=Decimal(10),
            per_share_usd=Decimal(1), tax_usd=Decimal("0.30"),
            foreign_tax_payment_date=date(2027, 1, 2),
            country_code="US", jurisdiction_level="FEDERAL",
            tax_type="WITHHOLDING_INCOME_TAX",
            date_evidence_source="BROKER_TAX_REPORT",
        ))
    pagamento = ev.foreign_tax_payments.get()
    ano_fechado(2026)
    pagamento.tax_usd = Decimal("0.50")
    with pytest.raises(ValidationError, match="fechado"):
        pagamento.save()


@pytest.mark.django_db
def test_ptax_override_bloqueia_ano_fechado(db, residente):
    ano_fechado(2026)
    with pytest.raises(ValidationError, match="fechado"):
        PtaxService().override(date(2026, 12, 31), Decimal("5.5"), "conferência manual")


@pytest.mark.django_db
def test_transferencia_bloqueia_ano_fechado(conta, residente):
    from ledger.service import BrokerTransferService
    destino = BrokerAccount.objects.create(broker_name="Outra", account_number="2")
    ano_fechado(2026)
    with pytest.raises(ValidationError, match="fechado"):
        BrokerTransferService().record(
            conta, destino, date(2026, 6, 1), amount_usd=Decimal(500),
        )


@pytest.mark.django_db
def test_reabrir_ano_libera_as_operacoes(conta, residente):
    """Regressão completa: bloqueia fechado → reabre → passa."""
    ano_fechado(2026)
    AnnualAssessment.objects.filter(year=2026).delete()
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        ev = EventService().record(dict(
            account=conta, event_type="APORTE",
            trade_date=date(2026, 6, 1), amount_usd=Decimal(1000),
        ))
    assert ev.pk