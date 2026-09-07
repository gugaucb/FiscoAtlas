from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from fiscal.report import ReportService
from fx.service import PtaxService
from ledger.models import BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def accounts(db, residente):
    from fiscal.models import TaxRule
    TaxRule.objects.create(tax_year=2026, rule_version="V2",
                           brackets=[{"limit_brl": None, "rate": "0.15"}],
                           confirmed=True, effective_from="2026-01-01", effective_until="2026-12-31")
    nao_remun = BrokerAccount.objects.create(broker_name="A", account_number="1", is_interest_bearing=False)
    remun = BrokerAccount.objects.create(broker_name="B", account_number="2", is_interest_bearing=True)
    return nao_remun, remun


def test_variacao_cambial_isenta(accounts):
    nao_remun, remun = accounts
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        # aporte 1000 USD (5000 BRL); nenhuma saída → saldo 1000 USD = 5000 BRL a PTAX 6
        EventService().record(dict(account=nao_remun, event_type="APORTE",
                                   trade_date=date(2026, 1, 2), amount_usd=Decimal(1000)))
        EventService().record(dict(account=remun, event_type="APORTE",
                                   trade_date=date(2026, 1, 2), amount_usd=Decimal(500)))
    with mock.patch.object(PtaxService, "get_rate") as get_rate:
        get_rate.return_value = mock.Mock(rate=Decimal("6.00000000"), effective_date=date(2026, 12, 31))
        report = ReportService(2026).build()
    exempt = {e["account"].pk: e for e in report["exempt"]["accounts"]}
    # 6000 BRL a PTAX 31/12 − 5000 BRL de entrada = 1000 isentos
    assert exempt[nao_remun.pk]["exempt_brl"] == Decimal("1000.00")
    # conta remunerada não entra
    assert remun.pk not in exempt
    assert report["exempt"]["total_brl"] == Decimal("1000.00")


def test_desvalorizacao_reporta_zero(accounts):
    nao_remun, _ = accounts
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(account=nao_remun, event_type="APORTE",
                                   trade_date=date(2026, 1, 2), amount_usd=Decimal(1000)))
    with mock.patch.object(PtaxService, "get_rate") as get_rate:
        get_rate.return_value = mock.Mock(rate=Decimal("4.00000000"), effective_date=date(2026, 12, 31))
        report = ReportService(2026).build()
    assert report["exempt"]["accounts"][0]["exempt_brl"] == Decimal("0")
    assert report["exempt"]["total_brl"] == Decimal("0")
