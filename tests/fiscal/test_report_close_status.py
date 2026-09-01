from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from fiscal.models import AnnualAssessment
from fiscal.report import ReportService
from fx.service import PtaxService
from ledger.models import BrokerAccount

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def rules(db):
    from fiscal.models import TaxRule
    for year in (2025, 2026):
        TaxRule.objects.create(tax_year=year, rule_version="V2",
                               brackets=[{"limit_brl": None, "rate": "0.15"}],
                               confirmed=True,
                               effective_from=f"{year}-01-01", effective_until=f"{year}-12-31")


def _report(year):
    with mock.patch.object(PtaxService, "get_rate") as get_rate:
        get_rate.return_value = mock.Mock(rate=RATE, effective_date=date(year, 12, 31))
        return ReportService(year).build()


def test_ano_fechado_no_relatorio(rules):
    BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    snap = _report(2025)  # garante que build funciona sem snapshot
    assert snap["closing"]["is_closed"] is False
    assert snap["closing"]["prev_closed"] is False

    AnnualAssessment.objects.create(
        year=2025, rule_version="V2", income_brl=0, loss_brl=0,
        taxable_brl=0, tax_brl=0, withholding_credit_brl=0, tax_due_brl=0,
        loss_carryforward_brl=0, detail=[], confirmed=True)
    report = _report(2025)
    assert report["closing"]["is_closed"] is True
    assert report["closing"]["prev_closed"] is False  # 2024 sem snapshot


def test_prev_closed_quando_ano_anterior_fechado(rules):
    BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    AnnualAssessment.objects.create(
        year=2024, rule_version="V2", income_brl=0, loss_brl=0,
        taxable_brl=0, tax_brl=0, withholding_credit_brl=0, tax_due_brl=0,
        loss_carryforward_brl=0, detail=[], confirmed=True)
    report = _report(2025)
    assert report["closing"]["prev_closed"] is True


def test_tela_relatorio_mostra_selo_e_aviso(client, rules):
    from fx.models import PtaxRate
    BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    PtaxRate.objects.create(requested_date=date(2025, 12, 31),
                            effective_date=date(2025, 12, 31), rate=RATE)
    page = client.get("/relatorio/2025/").content.decode()
    assert "Ano em aberto" in page
    assert "não está fechado" in page

    AnnualAssessment.objects.create(
        year=2024, rule_version="V2", income_brl=0, loss_brl=0,
        taxable_brl=0, tax_brl=0, withholding_credit_brl=0, tax_due_brl=0,
        loss_carryforward_brl=0, detail=[], confirmed=True)
    page = client.get("/relatorio/2025/").content.decode()
    assert "não está fechado" not in page

    AnnualAssessment.objects.create(
        year=2025, rule_version="V2", income_brl=0, loss_brl=0,
        taxable_brl=0, tax_brl=0, withholding_credit_brl=0, tax_due_brl=0,
        loss_carryforward_brl=0, detail=[], confirmed=True)
    page = client.get("/relatorio/2025/").content.decode()
    assert "Ano fechado" in page
    assert "Ano em aberto" not in page
