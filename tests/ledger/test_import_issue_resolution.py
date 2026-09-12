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


def _criar_evento(conta, ativo=True):
    aapl = Asset.objects.get_or_create(
        ticker="AAPL", defaults=dict(description="Apple", asset_type="FOREIGN_EQUITY"),
    )[0]
    with mock.patch("ledger.service.EventService._ptax_rate", return_value=RATE):
        return FinancialEvent.objects.create(
            account=conta, asset=aapl, event_type="APORTE", active=ativo,
            trade_date=date(2026, 2, 1), amount_usd=Decimal(100),
            fx_rate=RATE, amount_brl=Decimal(500),
        )


def test_reabertura_com_evento_inativo_e_revinculacao_ao_substituto(conta_com_pendencia, client):
    """Achado P1 do auditor (17): o ciclo completo da pendência. Issue
    vinculado ao evento #100; o evento é corrigido (desativado) → a
    pendência volta a ser aberta (regra computada, status gravado não é
    mutado) e pode ser re-vinculada ao evento substituto pela aplicação."""
    conta, issue = conta_com_pendencia
    ev1 = _criar_evento(conta)
    issue.resolve_imported(ev1)
    assert issue.status == ImportIssue.STATUS_RESOLVED_IMPORTED
    ev1.active = False
    ev1.save(update_fields=["active"])
    issue.refresh_from_db()
    assert issue.esta_aberta  # falha no código atual (RESOLVED_IMPORTED não era reaberta)
    assert issue.status == ImportIssue.STATUS_RESOLVED_IMPORTED  # trilha não mutada
    ev2 = _criar_evento(conta)
    issue.resolve_imported(ev2)
    issue.refresh_from_db()
    assert issue.resolved_event_id == ev2.pk
    assert "re-vinculação" in issue.resolution


def test_issue_reaberto_aparece_na_tela_de_pendencias(conta_com_pendencia, client):
    """Pendência reaberta aparece na lista de pendentes da UI — sem SQL manual."""
    conta, issue = conta_com_pendencia
    ev1 = _criar_evento(conta)
    issue.resolve_imported(ev1)
    ev1.active = False
    ev1.save(update_fields=["active"])
    resp = client.get(reverse("import-issues", args=[conta.pk]))
    pendentes = resp.context["pendentes"]
    assert issue.pk in {i.pk for i in pendentes}


def test_issue_reaberto_pode_ser_ignorado(conta_com_pendencia):
    conta, issue = conta_com_pendencia
    ev1 = _criar_evento(conta)
    issue.resolve_imported(ev1)
    ev1.active = False
    ev1.save(update_fields=["active"])
    issue.refresh_from_db()
    issue.resolve_ignored("lançamento substituto registrado à parte")
    issue.refresh_from_db()
    assert issue.status == ImportIssue.STATUS_RESOLVED_IGNORED
