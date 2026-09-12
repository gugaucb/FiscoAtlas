"""Ticket 27 (P0 do auditor) — patrimônio carregado entre anos.

Custódia > 0 e caixa ≠ 0 na data-base fazem a conta integrar histórico e
reconciliação, mesmo sem evento no ano e sem OpeningPosition explícita.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from django.core.exceptions import ValidationError

from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")


@pytest.fixture
def regra_2027(db, residente):
    from fiscal.models import TaxRule
    TaxRule.objects.create(
        tax_year=2027, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, effective_from="2027-01-01", effective_until="2027-12-31",
    )


def _conta(nome):
    return BrokerAccount.objects.create(broker_name=nome, account_number="1")


@pytest.mark.django_db
def test_reconciliacao_exige_extrato_com_custodia_carregada(residente, db):
    """AAPL comprado em 2026, nada em 2027, caixa zero → 31/12/2027 a conta
    continua tendo 100 AAPL em custódia e EXIGE extrato documentado."""
    from fiscal.reconciliation import AnnualReconciliationService

    conta = _conta("Custódia carregada")
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            account=conta, event_type="APORTE",
            trade_date=date(2026, 1, 2), amount_usd=Decimal(1100),
        ))
        EventService().record(dict(
            account=conta, event_type="BUY", asset=aapl,
            trade_date=date(2026, 1, 3), quantity=Decimal(100),
            price_usd=Decimal(10), fee_usd=Decimal(10),
        ))
    # 2027: nenhum evento, caixa 0, sem OpeningPosition
    svc = AnnualReconciliationService(2027)
    # falha no código atual: a conta nem era confrontada (caixa 0, sem
    # evento no ano, sem OpeningPosition explícita)
    with pytest.raises(ValidationError, match="Saldo documental"):
        svc.run_or_raise()


@pytest.mark.django_db
def test_conta_desativada_com_caixa_carregado_permanece_no_relatorio(regra_2027):
    """Conta desativada, sem evento em 2027, caixa carregado de 2026 ≠ 0 →
    permanece no relatório/histórico de 2027."""
    conta = _conta("Desativada com caixa")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            account=conta, event_type="APORTE",
            trade_date=date(2026, 3, 1), amount_usd=Decimal(20000),
        ))
    conta.active = False
    conta.save(update_fields=["active"])
    from fiscal.report import ReportService
    from unittest import mock as m
    from fx.service import PtaxService
    with m.patch.object(PtaxService, "get_rate") as get_rate:
        get_rate.return_value = m.Mock(rate=RATE, effective_date=date(2027, 12, 31))
        report = ReportService(2027).build()
    assert any(i["account_number"] == "1" for i in report["identification"])
    assert any(c["account"] == conta for c in report["cash"])


@pytest.mark.django_db
def test_conta_desativada_com_custodia_carregada_permanece_no_relatorio(regra_2027):
    """Conta desativada com posição carregada de 2025 (OpeningPosition) e
    sem evento em 2027 → permanece no relatório de 2027 (custódia real)."""
    from fiscal.report import ReportService
    from unittest import mock as m
    from fx.service import PtaxService
    from ledger.models import OpeningPosition

    conta = _conta("Desativada com custódia")
    aapl = Asset.objects.create(ticker="MSFT", description="Microsoft", asset_type="FOREIGN_EQUITY")
    OpeningPosition.objects.create(
        account=conta, asset=aapl, quantity=Decimal(50), total_cost_brl=Decimal(25000),
    )
    conta.active = False
    conta.save(update_fields=["active"])
    with m.patch.object(PtaxService, "get_rate") as get_rate:
        get_rate.return_value = m.Mock(rate=RATE, effective_date=date(2027, 12, 31))
        report = ReportService(2027).build()
    assert any(i["account_number"] == "1" for i in report["identification"])