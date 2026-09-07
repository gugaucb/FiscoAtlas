"""Ticket 13 (roadmap-compliance) — Guia orientativa do DARF código 0211.

RF-DARF-001/005, CT-029: saldo devedor da apuração anual gera orientação
formal (código 0211 — IRPF Ajuste Anual), cota única com vencimento no
último dia útil de abril e simulação de parcelamento em até 8 quotas com
juros Selic. Imposto devido < R$ 10,00 → dispensa legal de emissão
(art. 872, RIR/2018).
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from fiscal.darf import DarfGuideService
from fiscal.models import TaxRule

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


def test_saldo_devedor_gera_guia_0211(regra):
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        guia = DarfGuideService(2026).build(tax_due_brl=Decimal(1500))
    assert guia["codigo"] == "0211"
    assert guia["descricao"] == "IRPF — Declaração de Ajuste Anual"
    assert guia["cota_unica"]["valor"] == Decimal(1500)
    assert guia["cota_unica"]["vencimento"] == date(2027, 4, 30)  # sexta-feira, último dia útil de abril
    assert guia["parcelamento"]["n_quotas"] == 8
    assert guia["parcelamento"]["valor_quota"] == Decimal("187.50")
    assert "Selic" in guia["parcelamento"]["juros"]


def test_vencimento_eh_ultimo_dia_util_de_abril(regra):
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        guia = DarfGuideService(2027).build(tax_due_brl=Decimal(100))
    # abril/2028 termina domingo 30 → vencimento sexta 28
    assert guia["cota_unica"]["vencimento"] == date(2028, 4, 28)


def test_imposto_menor_que_dez_reais_dispensa(regra):
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        guia = DarfGuideService(2026).build(tax_due_brl=Decimal("9.99"))
    assert guia["dispensado"] is True
    assert "dispensada" in guia["mensagem"].lower()


def test_imposto_zero_gera_dispensa(regra):
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        guia = DarfGuideService(2026).build(tax_due_brl=Decimal(0))
    assert guia["dispensado"] is True


def test_guia_aparece_no_relatorio(regra):
    from fiscal.report import ReportService
    with mock.patch("fx.service.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        report = ReportService(2026).build()
    assert report["darf"]["codigo"] == "0211"
    assert report["darf"]["cota_unica"]["valor"] == Decimal("0.00")
