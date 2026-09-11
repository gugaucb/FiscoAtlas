"""Ticket 04 — edição manual do imposto pago no exterior com trilha de auditoria.

Alterar data documental, jurisdição, tipo ou evidência exige motivo e grava
old_value/new_value/changed_at. PTAX COMPRA manual exige motivo.
"""
from unittest import mock
from datetime import date
from decimal import Decimal

import pytest

from ledger.forms import ForeignTaxPaymentForm
from ledger.models import Asset, BrokerAccount, ForeignTaxPaymentAudit
from ledger.service import EventService

pytestmark = pytest.mark.django_db

RATE = Decimal("5.00000000")


@pytest.fixture
def pagamento(db):
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    asset, _ = Asset.objects.get_or_create(
        ticker="AAPL", defaults={"description": "Apple", "asset_type": "STOCK"},
    )
    ev = EventService().record(dict(
        event_type="DIVIDEND", account=conta, asset=asset, trade_date=date(2026, 3, 10),
        quantity=Decimal(10), per_share_usd=Decimal(10), tax_usd=Decimal(30),
        foreign_tax_payment_date=date(2026, 3, 12),
        date_evidence_source="BROKER_STATEMENT", country_code="US",
        jurisdiction_level="FEDERAL", tax_type="WITHHOLDING_INCOME_TAX",
    ))
    return ev.foreign_tax_payments.get()


def _form(pagamento, **campos):
    payload = {
        # ticket 04: tax_usd e country_code agora são campos editáveis do
        # formulário e entram no payload como qualquer outro fato
        "tax_usd": pagamento.tax_usd,
        "country_code": pagamento.country_code,
        "foreign_tax_payment_date": "2026-03-12",
        "jurisdiction_level": pagamento.jurisdiction_level,
        "tax_type": pagamento.tax_type,
        "date_evidence_source": pagamento.date_evidence_source,
        "source_document_id": pagamento.source_document_id,
        "source_reference": pagamento.source_reference,
        "reason": "Extrato corrigido",
    }
    payload.update(campos)
    return ForeignTaxPaymentForm(instance=pagamento, data=payload)


def test_editar_data_grava_trilha_old_new(pagamento):
    form = _form(pagamento, foreign_tax_payment_date="2026-03-15")
    assert form.is_valid()
    form.save()
    pagamento.refresh_from_db()
    assert pagamento.foreign_tax_payment_date == date(2026, 3, 15)
    trilha = ForeignTaxPaymentAudit.objects.get(payment=pagamento)
    campos = {c["field"]: c for c in trilha.changes}
    assert campos["foreign_tax_payment_date"]["old"] == "2026-03-12"
    assert campos["foreign_tax_payment_date"]["new"] == "2026-03-15"
    assert trilha.reason == "Extrato corrigido"
    assert trilha.changed_at is not None


def test_editar_jurisdicao_e_tipo_grava_trilha(pagamento):
    form = _form(pagamento, jurisdiction_level="STATE", tax_type="INCOME_TAX")
    assert form.is_valid()
    form.save()
    trilha = ForeignTaxPaymentAudit.objects.get(payment=pagamento)
    campos = {c["field"]: c for c in trilha.changes}
    assert campos["jurisdiction_level"]["old"] == "FEDERAL"
    assert campos["jurisdiction_level"]["new"] == "STATE"
    assert campos["tax_type"]["new"] == "INCOME_TAX"


def test_motivo_obrigatorio(pagamento):
    form = _form(pagamento, foreign_tax_payment_date="2026-03-15", reason="")
    assert not form.is_valid()
    assert "reason" in form.errors
    assert ForeignTaxPaymentAudit.objects.count() == 0


def test_sem_mudanca_nao_gera_trilha(pagamento):
    form = _form(pagamento)
    assert form.is_valid()
    form.save()
    assert ForeignTaxPaymentAudit.objects.count() == 0


def test_trilha_acumula_entradas(pagamento):
    form = _form(pagamento, foreign_tax_payment_date="2026-03-15")
    assert form.is_valid()
    form.save()
    form = _form(pagamento, jurisdiction_level="STATE")
    assert form.is_valid()
    form.save()
    assert ForeignTaxPaymentAudit.objects.filter(payment=pagamento).count() == 2


# --- view + trilha pelo navegador -------------------------------------------

def test_view_editar_grava_trilha(client, pagamento):
    resp = client.post(f"/imposto-exterior/{pagamento.pk}/editar/", {
        "tax_usd": pagamento.tax_usd,
        "country_code": pagamento.country_code,
        "foreign_tax_payment_date": "2026-03-15",
        "jurisdiction_level": pagamento.jurisdiction_level,
        "tax_type": pagamento.tax_type,
        "date_evidence_source": pagamento.date_evidence_source,
        "source_document_id": pagamento.source_document_id,
        "source_reference": pagamento.source_reference,
        "reason": "Data corrigida conforme extrato",
    })
    assert resp.status_code == 302
    pagamento.refresh_from_db()
    assert pagamento.foreign_tax_payment_date == date(2026, 3, 15)
    assert ForeignTaxPaymentAudit.objects.filter(payment=pagamento).count() == 1


def test_view_motivo_vazio_nao_salva(client, pagamento):
    resp = client.post(f"/imposto-exterior/{pagamento.pk}/editar/", {
        "foreign_tax_payment_date": "2026-03-15",
        "jurisdiction_level": pagamento.jurisdiction_level,
        "tax_type": pagamento.tax_type,
        "date_evidence_source": pagamento.date_evidence_source,
        "reason": "",
    })
    assert resp.status_code == 200
    pagamento.refresh_from_db()
    assert pagamento.foreign_tax_payment_date == date(2026, 3, 12)
    assert ForeignTaxPaymentAudit.objects.count() == 0


def test_view_pagina_mostra_trilha(client, pagamento):
    from django.utils import timezone
    ForeignTaxPaymentAudit.objects.create(
        payment=pagamento,
        changes=[{"field": "foreign_tax_payment_date", "old": "2026-03-12", "new": "2026-03-11"}],
        reason="Ajuste manual", changed_at=timezone.now(),
    )
    html = client.get(f"/imposto-exterior/{pagamento.pk}/editar/").content.decode()
    assert "Trilha de auditoria" in html
    assert "Ajuste manual" in html
    assert "2026-03-12 → 2026-03-11" in html


def test_ptax_compra_manual_grava_override_e_trilha(client, pagamento):
    from fx.models import PtaxRate
    with mock.patch("fx.service.PtaxService.get_rate", return_value=mock.Mock(rate=Decimal("4.80"))):
        resp = client.post(f"/imposto-exterior/{pagamento.pk}/editar/", {
            "tax_usd": pagamento.tax_usd,
            "country_code": pagamento.country_code,
            "foreign_tax_payment_date": "2026-03-12",
            "jurisdiction_level": pagamento.jurisdiction_level,
            "tax_type": pagamento.tax_type,
            "date_evidence_source": pagamento.date_evidence_source,
            "ptax_compra_manual": "4.75",
            "reason": "BCB sem cotação; valor do extrato",
        })
    assert resp.status_code == 302
    override = PtaxRate.objects.filter(quote_type="COMPRA", manually_overridden=True).get()
    assert override.rate == Decimal("4.75")
    assert override.override_reason == "BCB sem cotação; valor do extrato"
    trilha = ForeignTaxPaymentAudit.objects.get(payment=pagamento)
    assert {"field": "ptax_compra", "old": "4.80", "new": "4.75"} in trilha.changes
