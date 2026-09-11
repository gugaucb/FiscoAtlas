"""Ticket 02 (roadmap-compliance) — Residência fiscal e titularidade.

Regras: RF-PER-001..005, RF-VAL-001 (Lei 14.754/2023).
- TaxEngine só apura para residente fiscal pleno no Brasil;
- contas conjuntas demonstram atribuição proporcional no relatório.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from django.core.exceptions import ValidationError

from fiscal.engine import TaxEngine
from fiscal.models import Profile, TaxRule
from fiscal.report import ReportService
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def setup_com_residente(residente, db):
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, quote_type="VENDA", date_rule="INCOME_RECEIPT_DATE",
        effective_from=date(2026, 1, 1),
    )
    return BrokerAccount.objects.create(broker_name="Avenue", account_number="1", is_interest_bearing=True)


def _cenario_rendimento(conta):
    asset = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(account=conta, event_type="BUY", asset=asset,
                                   trade_date=date(2026, 1, 3), quantity=Decimal(10),
                                   price_usd=Decimal(100), fee_usd=Decimal(0)))
        EventService().record(dict(account=conta, event_type="SELL", asset=asset,
                                   trade_date=date(2026, 6, 1), quantity=Decimal(10),
                                   price_usd=Decimal(120), fee_usd=Decimal(0)))


def _compute():
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        return TaxEngine(2026).compute()


# ---------------------------------------------------------------- Profile

def test_profile_aceita_status_de_residencia():
    p = Profile.objects.create(name="G", cpf="000.000.000-00",
                               tax_residency_status="BRAZIL_RESIDENT",
                               residency_start_date=date(2015, 1, 1), has_dsdp=False)
    assert p.tax_residency_status == "BRAZIL_RESIDENT"
    assert p.has_dsdp is False


def test_engine_bloqueia_sem_profile():
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="x")
    with pytest.raises(ValidationError, match="não qualificado como residente fiscal pleno"):
        _compute()


@pytest.mark.parametrize("status", ["NON_RESIDENT", "PART_YEAR_RESIDENT", "UNKNOWN"])
def test_engine_bloqueia_nao_residente(status):
    Profile.objects.create(name="G", cpf="000.000.000-00", tax_residency_status=status)
    with pytest.raises(ValidationError, match="não qualificado como residente fiscal pleno"):
        _compute()


def test_engine_permite_residente_pleno(setup_com_residente):
    _cenario_rendimento(setup_com_residente)
    resultado = _compute()
    assert resultado["income_brl"] == Decimal("1000.00")


# ------------------------------------------------------------- titularidade

def test_brokeraccount_campos_de_titularidade():
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="2",
                                         ownership_type="JOINT", ownership_share=Decimal("50.00"))
    assert conta.ownership_type == "JOINT"
    assert conta.ownership_share == Decimal("50.00")


@pytest.mark.parametrize("share", [Decimal("100.01"), Decimal("-0.01")])
def test_brokeraccount_ownership_share_fora_do_intervalo(share):
    conta = BrokerAccount(broker_name="A", account_number="3", ownership_share=share)
    with pytest.raises(ValidationError):
        conta.full_clean()


def test_brokeraccount_ownership_share_zero_explicito_valido():
    """Ticket 06 (auditoria-fiscal): 0% é permitido como decisão EXPLÍCITA
    (conta de terceiros). O teste antigo proibia 0 na faixa inteira —
    substituído porque a regra fiscal silenciosa era o problema, não o valor."""
    conta = BrokerAccount(broker_name="A", account_number="3",
                          ownership_type="THIRD_PARTY", ownership_share=Decimal("0"))
    conta.full_clean()  # não levanta
    conta.save()
    assert conta.ownership_share == Decimal("0")


def test_relatorio_proporcional_conta_conjunta(residente):
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, quote_type="VENDA", date_rule="INCOME_RECEIPT_DATE",
        effective_from=date(2026, 1, 1),
    )
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="4",
                                         ownership_type="JOINT", ownership_share=Decimal("50.00"),
                                         is_interest_bearing=True)
    _cenario_rendimento(conta)
    with mock.patch("fiscal.report.PtaxService.get_rate",
                    return_value=mock.Mock(rate=RATE, effective_date=date(2026, 12, 31))):
        report = ReportService(2026).build()
    atribuicao = report["ownership_attribution"]
    linha = next(l for l in atribuicao if l["account"].pk == conta.pk)
    assert linha["share_pct"] == Decimal("50.00")
    # ganho de venda 10×120-10×100 = 200 USD × 5 = R$ 1.000 → 50% = R$ 500
    assert linha["income_brl_attrib"] == Decimal("500.00")
    # custódia: 0 ações restantes; caixa: 10000-10000+12000 = 2000? Não:
    # apenas 1000 (compra) e +1200 (venda) → 200 USD × 5 = R$ 1.000 → 50% = 500
    assert linha["custody_brl_attrib"] == Decimal("0.00")
    assert linha["cash_brl_attrib"] == Decimal("500.00")


def test_conta_individual_atribuicao_integral(residente):
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, quote_type="VENDA", date_rule="INCOME_RECEIPT_DATE",
        effective_from=date(2026, 1, 1),
    )
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="5")
    _cenario_rendimento(conta)
    with mock.patch("fiscal.report.PtaxService.get_rate",
                    return_value=mock.Mock(rate=RATE, effective_date=date(2026, 12, 31))):
        report = ReportService(2026).build()
    linha = next(l for l in report["ownership_attribution"] if l["account"].pk == conta.pk)
    assert linha["share_pct"] == Decimal("100.00")
    assert linha["income_brl_attrib"] == Decimal("1000.00")


# ------------------------------------------------------------------- form

def test_form_perfil_salva_residencia(client):
    resp = client.post("/perfil/", {
        "name": "Gustavo", "cpf": "000.000.000-00",
        "tax_residency_status": "BRAZIL_RESIDENT",
        "residency_start_date": "2015-01-01", "has_dsdp": "on",
    })
    assert resp.status_code == 302
    p = Profile.objects.first()
    assert p.tax_residency_status == "BRAZIL_RESIDENT"
    assert p.residency_start_date == date(2015, 1, 1)
    assert p.has_dsdp is True
