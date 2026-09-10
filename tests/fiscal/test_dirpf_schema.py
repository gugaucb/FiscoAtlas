"""Ticket 11 (roadmap-compliance) — Schema versionado da DIRPF.

RF-ARQ-002/003, RF-DIR-005/013: códigos da ficha Bens e Direitos por
exercício (DirpfSchema) com trava de homologação — exercício sem IN
homologada gera relatório PRELIMINAR.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from fiscal.models import DirpfSchema, TaxRule
from ledger.models import BrokerAccount

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
    return BrokerAccount.objects.create(broker_name="Avenue", account_number="1")


def _report(year):
    from fiscal.report import ReportService
    with mock.patch("fx.service.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        return ReportService(year).build()


def test_schema_por_exercicio_pode_ser_cadastrado(db):
    schema = DirpfSchema.objects.create(
        filing_year=2026, schema_version="DIRPF/2026-v1",
        groups={"FOREIGN_EQUITY": "03/01"},
        countries={"US": ("249", "Estados Unidos")},
        is_homologated=False,
    )
    assert schema.filing_year == 2026
    assert DirpfSchema.objects.get(filing_year=2026) == schema


def test_sem_schema_relatorio_preliminar_com_aviso(ambiente):
    """Ticket 11 (auditoria-fiscal): o teste antigo esperava HOMOLOGADO com
    defaults — substituído porque um relatório sem base versionada não pode
    se apresentar como definitivo. Sem schema → PRELIMINAR com aviso; a
    apuração matemática continua funcionando."""
    report = _report(2026)
    assert report["dirpf"]["status"] == "PRELIMINAR"
    assert report["dirpf"]["schema_version"] == "default"
    assert "PRELIMINAR" in report["dirpf"]["aviso"]
    # apuração matemática segue funcionando sem schema
    assert report["income"] is not None
    assert "assets" in report


def test_schema_nao_homologado_marca_relatorio_preliminar(ambiente):
    DirpfSchema.objects.create(
        filing_year=2026, schema_version="DIRPF/2026-v1",
        groups={}, countries={}, is_homologated=False,
    )
    report = _report(2026)
    assert report["dirpf"]["status"] == "PRELIMINAR"
    assert report["dirpf"]["schema_version"] == "DIRPF/2026-v1"


def test_schema_homologado_marca_relatorio_homologado(ambiente):
    DirpfSchema.objects.create(
        filing_year=2026, schema_version="DIRPF/2026-v1",
        groups={}, countries={}, is_homologated=True,
    )
    report = _report(2026)
    assert report["dirpf"]["status"] == "HOMOLOGADO"


def test_codigos_do_schema_sobrescrevem_defaults(ambiente):
    DirpfSchema.objects.create(
        filing_year=2026, schema_version="DIRPF/2026-v1",
        groups={"FOREIGN_EQUITY": "03/77", "FOREIGN_ETF": "03/02", "REIT": "03/03",
                "FOREIGN_FUND": "03/99", "US_TREASURY": "04/99",
                "FOREIGN_BOND": "04/99", "OTHER": "99/99"},
        countries={"US": ("249", "Estados Unidos")}, is_homologated=True,
    )
    from ledger.models import Asset
    from ledger.service import EventService
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="BUY", account=ambiente, asset=aapl,
            trade_date=date(2026, 1, 5), quantity=Decimal(10),
            price_usd=Decimal(100), fee_usd=Decimal(0),
        ))
    report = _report(2026)
    assert report["assets"][0]["grupo_codigo"] == "03/77"
