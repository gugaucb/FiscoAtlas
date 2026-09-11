"""Ticket 05 (roadmap-compliance) — Validador bloqueante de fechamento anual.

RF-VAL-001..020: o fechamento (`AnnualAssessment.confirmed = True`) só pode
ocorrer se as precondições fiscais do ano estiverem íntegras. Violações são
coletadas e apresentadas juntas com mensagens explicativas.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from django.core.exceptions import ValidationError

from fiscal.engine import TaxEngine
from fiscal.models import AnnualAssessment, TaxRule
from fiscal.validator import AnnualClosingValidator
from ledger.models import Asset, BrokerAccount, FinancialEvent, ForeignTaxPayment
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
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="1", is_interest_bearing=True)
    return conta


def _compra(conta, ticker="AAPL", qty=Decimal(10), price=Decimal(100), dia=date(2026, 1, 5)):
    asset = Asset.objects.get_or_create(
        ticker=ticker, defaults={"description": ticker, "asset_type": "FOREIGN_EQUITY"}
    )[0]
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(dict(
            event_type="BUY", account=conta, asset=asset, trade_date=dia,
            quantity=qty, price_usd=price, fee_usd=Decimal(0),
        ))


def _dividendo_com_imposto(conta, tax_usd=Decimal(10), per_share=Decimal(1)):
    asset = Asset.objects.get_or_create(
        ticker="AAPL", defaults={"description": "Apple", "asset_type": "FOREIGN_EQUITY"}
    )[0]
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        ev = EventService().record(dict(
            event_type="DIVIDEND", account=conta, asset=asset,
            trade_date=date(2026, 3, 1), quantity=Decimal(10),
            per_share_usd=per_share, tax_usd=tax_usd,
            foreign_tax_payment_date=date(2026, 3, 1), confirm_same_day=False,
            date_evidence_source="BROKER_STATEMENT", country_code="US",
            jurisdiction_level="FEDERAL", tax_type="WITHHOLDING_INCOME_TAX",
        ))
    return ev


# ------------------------------------------------- cenário íntegro passa

def test_ano_integro_passa(ambiente):
    conta = ambiente
    _compra(conta)
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="SELL", account=conta, asset=Asset.objects.get(ticker="AAPL"),
            trade_date=date(2026, 6, 1), quantity=Decimal(5), price_usd=Decimal(110),
            fee_usd=Decimal(0),
        ))
    AnnualClosingValidator(2026).validate_or_raise()  # não levanta


# ------------------------------------------------- RF-VAL-001 residência

def test_bloqueia_sem_residencia_confirmada(ambiente):
    from fiscal.models import Profile
    Profile.objects.update(tax_residency_status="UNKNOWN")
    with pytest.raises(ValidationError, match="residente"):
        AnnualClosingValidator(2026).validate_or_raise()


def test_bloqueia_sem_profile(ambiente):
    from fiscal.models import Profile
    Profile.objects.all().delete()
    with pytest.raises(ValidationError, match="residente"):
        AnnualClosingValidator(2026).validate_or_raise()


# ------------------------------------------------- RF-VAL-002 ativo UNKNOWN

def test_bloqueia_ativo_unknown_com_evento(ambiente):
    conta = ambiente
    asset = Asset.objects.create(ticker="XYZ", description="?", asset_type="UNKNOWN")
    FinancialEvent.objects.create(
        event_type="DIVIDEND", account=conta, asset=asset, trade_date=date(2026, 3, 1),
        quantity=Decimal(1), amount_usd=Decimal(1), fx_rate=RATE, amount_brl=Decimal(5),
    )
    with pytest.raises(ValidationError, match="UNKNOWN"):
        AnnualClosingValidator(2026).validate_or_raise()


# ------------------------------------------------- integridade cambial

def test_bloqueia_evento_sem_amount_brl(ambiente):
    conta = ambiente
    ev = _compra(conta)
    FinancialEvent.objects.filter(pk=ev.pk).update(amount_brl=None)
    with pytest.raises(ValidationError, match="amount_brl"):
        AnnualClosingValidator(2026).validate_or_raise()


def test_bloqueia_evento_sem_fx_rate(ambiente):
    conta = ambiente
    ev = _compra(conta)
    FinancialEvent.objects.filter(pk=ev.pk).update(fx_rate=None)
    with pytest.raises(ValidationError, match="fx_rate"):
        AnnualClosingValidator(2026).validate_or_raise()


# ------------------------------------------------- venda a descoberto

def test_bloqueia_venda_acima_da_custodia(ambiente):
    conta = ambiente
    ev = _compra(conta, qty=Decimal(5))
    # venda direta (acima do saldo) — cria evento sem passar pelo service
    FinancialEvent.objects.create(
        event_type="SELL", account=conta, asset=ev.asset, trade_date=date(2026, 6, 1),
        quantity=Decimal(99), price_usd=Decimal(110), amount_usd=Decimal("10890"),
        fx_rate=RATE, amount_brl=Decimal(54450), fee_usd=Decimal(0),
    )
    with pytest.raises(ValidationError, match="custódia"):
        AnnualClosingValidator(2026).validate_or_raise()


def test_venda_integral_da_posicao_passa(ambiente):
    """Liquidar 100% da posição é legítimo: a custódia comparada deve ser
    a ANTERIOR à venda (position(until=trade_date) inclui a própria venda e
    zeraria o saldo, acusando venda a descoberto indevidamente)."""
    conta = ambiente
    ev = _compra(conta, qty=Decimal(20))
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="SELL", account=conta, asset=ev.asset,
            trade_date=date(2026, 6, 1), quantity=Decimal(20),
            price_usd=Decimal(110), fee_usd=Decimal(0),
        ))
    AnnualClosingValidator(2026).validate_or_raise()  # não levanta


# ------------------------------------------------- crédito exterior (ticket 05)

def test_retencao_30_porcento_nao_bloqueia_fechamento(ambiente):
    """Ticket 05 (auditoria-fiscal): os testes antigos bloqueavam retenção
    > 15% do bruto e crédito limitado ao IR (excesso sem carryforward) —
    substituídos porque uma retenção estrangeira maior (ex.: 30% dos EUA) é
    legítima; a lei limita o crédito aproveitável ao IR devido e o excedente
    é apenas não aproveitado (sem carryforward). Fechamento passa."""
    conta = ambiente
    # bruto = 10 × 1 + 10 = US$ 20; retido US$ 10 = 50% do bruto
    _dividendo_com_imposto(conta, tax_usd=Decimal(10))
    AnnualClosingValidator(2026).validate_or_raise()  # não levanta


def test_retencao_30_porcento_relatorio_segrega_aproveitado(ambiente):
    """Exemplo do auditor (PTAX 5): bruto 100 USD = R$ 500; imposto pago
    30 USD = R$ 150; IR devido 15% = R$ 75 → pago = 150, elegível = 150,
    aproveitado = 75, não aproveitado = 75 (descartado — sem carryforward)."""
    from fiscal.report import ReportService
    conta = ambiente
    _dividendo_com_imposto(conta, tax_usd=Decimal(30), per_share=Decimal(10))
    with mock.patch("fiscal.report.PtaxService.get_rate",
                    return_value=mock.Mock(rate=RATE, effective_date=date(2026, 12, 31))):
        report = ReportService(2026).build()
    linha = report["income"]["credit_detail"][0]
    assert linha["withholding_brl"] == Decimal("150.00")
    assert linha["limit_brl"] == Decimal("75.00")
    assert linha["credit_used_brl"] == Decimal("75.00")
    assert linha["credit_unused_brl"] == Decimal("75.00")
    assert linha["credit_eligible"] is True


def test_pagamento_unknown_bloqueia_fechamento_com_orientacao(ambiente):
    """Único bloqueio do crédito exterior: tratamento fiscal desconhecido
    (UNKNOWN) — exige classificação explícita, sem regra silenciosa."""
    conta = ambiente
    ev = _dividendo_com_imposto(conta, tax_usd=Decimal(10))
    pagamento = ev.foreign_tax_payments.get()
    pagamento.jurisdiction_level = "UNKNOWN"
    pagamento.save()
    with pytest.raises(ValidationError, match="classifique"):
        AnnualClosingValidator(2026).validate_or_raise()


# ------------------------------------------------- mensagens agregadas

def test_violacoes_sao_agregadas(ambiente):
    conta = ambiente
    _compra(conta)
    FinancialEvent.objects.create(
        event_type="DIVIDEND", account=conta, asset=Asset.objects.get(ticker="AAPL"),
        trade_date=date(2026, 3, 1), quantity=Decimal(1), amount_usd=Decimal(1),
        fx_rate=None, amount_brl=None,
    )
    from fiscal.models import Profile
    Profile.objects.update(tax_residency_status="NON_RESIDENT")
    with pytest.raises(ValidationError) as excinfo:
        AnnualClosingValidator(2026).validate_or_raise()
    msgs = " ".join(excinfo.value.messages)
    assert "residente" in msgs and "amount_brl" in msgs


# ------------------------------------------------- plugado na view

def test_close_year_view_bloqueado(ambiente, client):
    """Ticket 05: o bloqueio antigo era retenção > 15% — substituído porque
    retenção maior é legítima. O bloqueio passa a ser pagamento com
    tratamento fiscal desconhecido (UNKNOWN)."""
    conta = ambiente
    ev = _dividendo_com_imposto(conta, tax_usd=Decimal(10))
    pagamento = ev.foreign_tax_payments.get()
    pagamento.jurisdiction_level = "UNKNOWN"
    pagamento.save()
    resp = client.post("/apuracao/2026/fechar/")
    assert resp.status_code == 302  # redireciona de volta com mensagens de erro
    assert not AnnualAssessment.objects.filter(year=2026, confirmed=True).exists()


def test_dividendo_recebido_no_ano_seguinte_validado_no_ano_do_recebimento(ambiente):
    """P0 do auditor (efeito do ticket 10 no validador): o AnnualClosingValidator
    filtrava por trade_date__year — dividendo negociado 31/12/2026 e recebido
    02/01/2027 era APURADO em 2027 mas VALIDADO em 2026, escapando das
    verificações (crédito exterior UNKNOWN, ativo UNKNOWN, integridade cambial)
    do ano em que o rendimento é tributado."""
    conta = ambiente
    ev = _dividendo_com_imposto(conta, tax_usd=Decimal(10))
    FinancialEvent.objects.filter(pk=ev.pk).update(
        trade_date=date(2026, 12, 31), income_receipt_date=date(2027, 1, 2),
    )
    TaxRule.objects.create(
        tax_year=2027, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, effective_from=date(2027, 1, 1),
    )
    # pagamento com fatos UNKNOWN deve bloquear 2027 (não 2026)
    pagamento = ev.foreign_tax_payments.get()
    pagamento.jurisdiction_level = "UNKNOWN"
    pagamento.save()
    with pytest.raises(ValidationError, match="(?i)classifique"):
        AnnualClosingValidator(2027).validate_or_raise()
    AnnualClosingValidator(2026).validate_or_raise()  # não levanta


def test_dividendo_recebido_no_ano_seguinte_ativo_unknown_validado_em_2027(ambiente):
    """Mesma correção para RF-VAL-002: ativo UNKNOWN movimentado por rendimento
    recebido em 2027 é exigência de classificação no fechamento de 2027."""
    conta = ambiente
    asset = Asset.objects.create(ticker="XYZ", description="?", asset_type="UNKNOWN")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="DIVIDEND", account=conta, asset=asset,
            trade_date=date(2026, 12, 31), quantity=Decimal(1),
            per_share_usd=Decimal(1), income_receipt_date=date(2027, 1, 2),
        ))
    with pytest.raises(ValidationError, match="UNKNOWN"):
        AnnualClosingValidator(2027).validate_or_raise()


def test_close_year_view_ok(ambiente, client):
    """Auditoria-fiscal 12: o fechamento agora exige reconciliação ANTES da
    validação fiscal — saldo documental confirmado confrontando o ledger."""
    conta = ambiente
    _compra(conta)
    from ledger.models import DocumentedBalance
    DocumentedBalance.objects.create(
        account=conta, reference_date=date(2026, 12, 31),
        cash_usd=Decimal("-1000.00"), positions=[{"ticker": "AAPL", "quantity": "10"}],
        confirmed=True,
    )
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        resp = client.post("/apuracao/2026/fechar/")
    assert resp.status_code == 302
    assert AnnualAssessment.objects.get(year=2026).confirmed
