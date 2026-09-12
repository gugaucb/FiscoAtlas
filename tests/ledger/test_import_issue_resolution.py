"""P1 auditor: resolver ImportIssue pela aplicação.

O importador cria pendências PENDING e a reconciliação bloqueia o
fechamento enquanto existirem — sem UI de resolução o usuário entraria
em beco sem saída operacional (obrigado a editar o banco manualmente).
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from django.urls import reverse

from ledger.importers.schwab import SchwabStatementImporter
from ledger.models import Asset, BrokerAccount, FinancialEvent, ImportIssue

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


CSV = (
    "Date,Action,Symbol,Description,Quantity,Price,Fees & Comm,Amount\n"
    "01/02/2026,Transfer,,,,,,100.00\n"
)


@pytest.fixture
def conta_com_pendencia(db, residente):
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    batch = SchwabStatementImporter(conta).import_csv(CSV, acknowledge_pending=True)
    issue = ImportIssue.objects.get(batch=batch)
    assert issue.status == ImportIssue.STATUS_PENDING
    return conta, issue


def test_resolver_vinculando_evento(conta_com_pendencia, client):
    """Registrar lançamento correspondente: RESOLVED_IMPORTED + resolved_at."""
    conta, issue = conta_com_pendencia
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    with mock.patch("ledger.service.EventService._ptax_rate", return_value=RATE):
        evento = FinancialEvent.objects.create(
            account=conta, asset=aapl, event_type="APORTE",
            trade_date=date(2026, 2, 1), amount_usd=Decimal(100),
            fx_rate=RATE, amount_brl=Decimal(500),
        )
    url = reverse("import-issues", args=[conta.pk])
    resp = client.post(url, {"issue_pk": issue.pk, "acao": "vincular", "event_pk": evento.pk})
    issue.refresh_from_db()
    # P1 auditor: vínculo é FK real (trilha auditável), não ID em string
    assert issue.resolved_event_id == evento.pk
    assert issue.status == ImportIssue.STATUS_RESOLVED_IMPORTED
    assert issue.resolved_at is not None


def test_vinculo_exige_mesma_conta(conta_com_pendencia, client):
    """Evento de outra conta não resolve a pendência da conta original."""
    outra = BrokerAccount.objects.create(broker_name="Interactive", account_number="2")
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    evento = FinancialEvent.objects.create(
        account=outra, asset=aapl, event_type="APORTE",
        trade_date=date(2026, 2, 1), amount_usd=Decimal(100),
        fx_rate=RATE, amount_brl=Decimal(500),
    )
    conta, issue = conta_com_pendencia
    client.post(
        reverse("import-issues", args=[conta.pk]),
        {"issue_pk": issue.pk, "acao": "vincular", "event_pk": evento.pk},
    )
    issue.refresh_from_db()
    assert issue.status == ImportIssue.STATUS_PENDING
    assert issue.resolved_at is None


def test_ignorar_sem_justificativa_bloqueia(conta_com_pendencia, client):
    conta, issue = conta_com_pendencia
    client.post(
        reverse("import-issues", args=[conta.pk]),
        {"issue_pk": issue.pk, "acao": "ignorar", "justificativa": "   "},
    )
    issue.refresh_from_db()
    assert issue.status == ImportIssue.STATUS_PENDING


def test_ignorar_com_justificativa(conta_com_pendencia, client):
    """Ignorar exige justificativa: RESOLVED_IGNORED + resolved_at."""
    conta, issue = conta_com_pendencia
    client.post(
        reverse("import-issues", args=[conta.pk]),
        {"issue_pk": issue.pk, "acao": "ignorar", "justificativa": "Transferência entre contas próprias"},
    )
    issue.refresh_from_db()
    assert issue.status == ImportIssue.STATUS_RESOLVED_IGNORED
    assert issue.resolved_at is not None
    assert issue.resolution == "Transferência entre contas próprias"


def test_vinculo_exige_evento_ativo(conta_com_pendencia):
    """P1 auditor: evento desativado/corrigido não é lançamento fiscal
    válido — não pode liberar o bloqueio da pendência."""
    conta, issue = conta_com_pendencia
    aapl = Asset.objects.create(ticker="MSFT", description="Microsoft", asset_type="FOREIGN_EQUITY")
    evento = FinancialEvent.objects.create(
        account=conta, asset=aapl, event_type="APORTE", active=False,
        trade_date=date(2026, 2, 1), amount_usd=Decimal(100),
        fx_rate=RATE, amount_brl=Decimal(500),
    )
    with pytest.raises(ValueError, match="deve estar ativo"):
        issue.resolve_imported(evento)
    issue.refresh_from_db()
    assert issue.status == ImportIssue.STATUS_PENDING
    assert issue.resolved_event_id is None


def test_issue_ja_resolvido_nao_resolve_de_novo(conta_com_pendencia, client):
    conta, issue = conta_com_pendencia
    issue.resolve_ignored("teste")
    with pytest.raises(ValueError, match="já está resolvida"):
        issue.resolve_ignored("outra justificativa")
