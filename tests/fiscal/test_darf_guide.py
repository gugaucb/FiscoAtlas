"""Ticket 08 (auditoria-fiscal) — DARF versionado por exercício (FilingRule).

Regras de arrecadação saem do código fixo e viram modelo por exercício
(ano-calendário 2026 → exercício 2027). Sem regra homologada, orientação
PRELIMINAR — nunca vencimento/código inventados. Parcelamento respeita
quota mínima, imposto mínimo e máximo (não divisão automática por 8).
DARF < R$ 10 é ADIAMENTO com acúmulo (art. 938, §§ 4º e 5º, RIR/2018).
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from fiscal.darf import DarfGuideService
from fiscal.models import FilingRule, TaxRule

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def regra(residente, db):
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, quote_type="VENDA", date_rule="INCOME_RECEIPT_DATE",
        effective_from=date(2026, 1, 1),
    )
    return FilingRule.objects.create(
        filing_year=2027, rule_version="DARF/2027-v1",
        due_date=date(2027, 4, 30), darf_code="0211",
        minimum_darf=Decimal(10), minimum_installment=Decimal(100),
        minimum_tax_for_installment=Decimal(100), maximum_installments=8,
        is_homologated=True,
        legal_basis="RIR/2018, art. 938, §§ 4º e 5º",
    )


def test_sem_regra_homologada_orientacao_preliminar(regra, db):
    """Regressão ticket 08: antes, vencimento/código eram calculados de
    constantes hardcoded e a guia aparecia como definitiva. Sem regra →
    PRELIMINAR, sem data inventada."""
    FilingRule.objects.all().delete()
    guia = DarfGuideService(2026).build(tax_due_brl=Decimal(1500))
    assert guia["status"] == "PRELIMINAR"
    assert "PRELIMINAR" in guia["aviso"]
    assert guia["codigo"] is None
    assert guia["vencimento"] is None
    assert guia["parcelamento"] is None
    assert guia["cota_unica"]["valor"] == Decimal("1500.00")


def test_regra_nao_homologada_fica_preliminar(regra, db):
    regra.is_homologated = False
    regra.save()
    guia = DarfGuideService(2026).build(tax_due_brl=Decimal(1500))
    assert guia["status"] == "PRELIMINAR"
    assert "não está homologada" in guia["aviso"]


def test_filing_year_eh_ano_calendario_mais_um(regra, db):
    """ano-calendário 2026 → exercício 2027: regra de 2027 é usada; regra de
    outro exercício não é."""
    FilingRule.objects.all().delete()
    FilingRule.objects.create(
        filing_year=2026, rule_version="ERRADA",
        due_date=date(2026, 4, 30), darf_code="9999",
        minimum_darf=Decimal(10), minimum_installment=Decimal(100),
        minimum_tax_for_installment=Decimal(100), maximum_installments=8,
        is_homologated=True,
    )
    guia = DarfGuideService(2026).build(tax_due_brl=Decimal(1500))
    assert guia["status"] == "PRELIMINAR"  # exercício 2027 sem regra
    assert guia["exercicio"] == 2027


def test_guia_homologada_cota_unica_e_parcelamento_8_quota_maxima(regra):
    guia = DarfGuideService(2026).build(tax_due_brl=Decimal(1500))
    assert guia["status"] == "HOMOLOGADO"
    assert guia["codigo"] == "0211"
    assert guia["vencimento"] == date(2027, 4, 30)
    assert guia["cota_unica"]["valor"] == Decimal(1500)
    # 1500/8 = 187,50 ≥ quota mínima 100 → máximo de quotas
    assert guia["parcelamento"]["n_quotas"] == 8
    assert guia["parcelamento"]["valor_quota"] == Decimal("187.50")
    assert "Selic" in guia["parcelamento"]["juros"]


def test_parcelamento_respeita_quota_minima(regra):
    """Regressão ticket 08 (falha no código atual, que dividia por 8):
    R$ 99 → quota única (99 < quota mínima 100); R$ 100 → 1 quota;
    R$ 300 → 3 quotas de R$ 100 (300/8 = 37,50 < 100, desce até 3)."""
    guia99 = DarfGuideService(2026).build(tax_due_brl=Decimal(99))
    assert guia99["parcelamento"]["n_quotas"] == 1
    assert guia99["parcelamento"]["valor_quota"] == Decimal("99.00")
    guia100 = DarfGuideService(2026).build(tax_due_brl=Decimal(100))
    assert guia100["parcelamento"]["n_quotas"] == 1
    guia300 = DarfGuideService(2026).build(tax_due_brl=Decimal(300))
    assert guia300["parcelamento"]["n_quotas"] == 3
    assert guia300["parcelamento"]["valor_quota"] == Decimal("100.00")


def test_darf_menor_que_dez_eh_adiamento_nao_extincao(regra):
    """Ticket 02/08: o teste anterior chamava o valor de 'dispensado' —
    nomenclatura que induzia a entender imposto extinto. É ADIAMENTO: o
    valor se acumula ao mesmo código nos períodos subsequentes."""
    guia = DarfGuideService(2026).build(tax_due_brl=Decimal("9.99"))
    assert guia["adiado"] is True
    assert guia["payment_required_now"] is False
    assert "art. 938, § 4º" in guia["mensagem"]
    assert "art. 938, § 5º" in guia["mensagem"]
    assert "permanece devido" in guia["mensagem"]
    assert "872" not in guia["mensagem"]


def test_imposto_zero_nao_exige_pagamento(regra):
    guia = DarfGuideService(2026).build(tax_due_brl=Decimal(0))
    assert guia["adiado"] is True
    assert guia["payment_required_now"] is False


def test_guia_aparece_no_relatorio(regra):
    from fiscal.report import ReportService
    with mock.patch("fx.service.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        report = ReportService(2026).build()
    assert report["darf"]["status"] == "HOMOLOGADO"
    assert report["darf"]["codigo"] == "0211"
    assert report["darf"]["cota_unica"]["valor"] == Decimal("0.00")