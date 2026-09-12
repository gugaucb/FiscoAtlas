"""Ticket 26 (P0 do auditor) — reabrir o ano devolve compensações.

O fechamento consome prejuízo FIFO via LossLedgerService.apply_compensation.
A reabertura não pode deixar o saldo consumido: devolve cada LossCompensation
do ano ao registro de origem, apaga as compensações e o snapshot, tudo na
MESMA transação.
"""
import pytest
from decimal import Decimal

from fiscal.losses import LossLedgerService
from fiscal.models import AnnualAssessment, TaxRule

pytestmark = pytest.mark.django_db


@pytest.fixture
def rules(db, residente):
    TaxRule.objects.create(tax_year=2025, rule_version="V2",
                           brackets=[{"limit_brl": None, "rate": "0.15"}],
                           confirmed=True,
                           effective_from="2025-01-01", effective_until="2025-12-31")


def test_reabrir_devolve_prejuizo_consumido(client, rules):
    """P0 do auditor: prejuízo 1.000; fechamento 2025 consome 600 (saldo
    400); reabrir 2025 → saldo volta a 1.000 e compensações zeradas."""
    record = LossLedgerService.record_loss(2024, Decimal("1000"), description="venda 2024")
    AnnualAssessment.objects.create(
        year=2025, rule_version="V2", income_brl=600, loss_brl=0,
        taxable_brl=0, tax_brl=0, withholding_credit_brl=0, tax_due_brl=0,
        loss_carryforward_brl=0, detail=[], confirmed=True,
    )
    compensado = LossLedgerService.apply_compensation(2025, Decimal("600"))
    assert compensado == Decimal("600")
    record.refresh_from_db()
    assert record.remaining_brl == Decimal("400")

    client.post("/apuracao/2025/reabrir/", {"confirmar": "2025"})

    record.refresh_from_db()
    assert record.remaining_brl == Decimal("1000")
    assert not record.compensations.filter(year=2025).exists()
    assert not AnnualAssessment.objects.filter(year=2025).exists()
    assert LossLedgerService.available(until_year=2025) == Decimal("1000")


def test_reabrir_sem_compensacoes_nao_falha(client, rules):
    """Ano fechado sem consumo de prejuízo: reabertura segue funcionando."""
    client.post("/apuracao/2025/fechar/")
    resp = client.post("/apuracao/2025/reabrir/", {"confirmar": "2025"})
    assert resp.status_code == 302
    assert not AnnualAssessment.objects.filter(year=2025).exists()


def test_reabrir_bloqueio_de_ano_posterior_usa_confirmed(client, rules):
    """Snapshot posterior NÃO confirmado (fechamento em andamento) não
    bloqueia a reabertura — só confirmed=True congela."""
    AnnualAssessment.objects.create(
        year=2026, rule_version="V2", income_brl=0, loss_brl=0,
        taxable_brl=0, tax_brl=0, withholding_credit_brl=0, tax_due_brl=0,
        loss_carryforward_brl=0, detail=[], confirmed=False,
    )
    AnnualAssessment.objects.create(
        year=2025, rule_version="V2", income_brl=0, loss_brl=0,
        taxable_brl=0, tax_brl=0, withholding_credit_brl=0, tax_due_brl=0,
        loss_carryforward_brl=0, detail=[], confirmed=True,
    )
    resp = client.post("/apuracao/2025/reabrir/", {"confirmar": "2025"})
    assert resp.status_code == 302
    assert not AnnualAssessment.objects.filter(year=2025).exists()