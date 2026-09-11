"""Auditoria-fiscal 12 — reconciliação anual separada do validador fiscal.

Antes do ticket, o fechamento só aplicava regras fiscais: uma pendência de
importação descoberta depois, um caixa que não concilia com o extrato ou um
rendimento com retenção presumidamente zero passavam despercebidos. A
reconciliação responde "os dados de ENTRADA estão completos e conciliados?"
— o validador responde "as regras FISCAIS estão íntegras?".
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from fiscal.models import TaxRule
from fiscal.reconciliation import AnnualReconciliationService
from ledger.importers.schwab import SchwabStatementImporter
from ledger.models import Asset, BrokerAccount, DocumentedBalance
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def ambiente(db, residente):
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, effective_from=date(2026, 1, 1),
    )
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    return conta


def _aporte(conta, amount, dia=date(2026, 1, 5)):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="APORTE", account=conta, trade_date=dia, amount_usd=amount,
        ))


def _doc(conta, cash, positions=None, confirmed=True):
    return DocumentedBalance.objects.create(
        account=conta, reference_date=date(2026, 12, 31),
        cash_usd=cash, positions=positions or [], confirmed=confirmed,
    )


CSV_COM_PENDENCIA = (
    "Date,Action,Symbol,Quantity,Price,Amount,Fees\n"
    "12/31/2026,Transfer Out,AAPL,10,0.00,0.00,0.00\n"
)


def test_pendencia_importacao_com_evento_no_ano_bloqueia(ambiente):
    """Falha no código atual: não havia reconciliação — pendência de importação
    descoberta depois não impedia o fechamento do ano do evento."""
    conta = ambiente
    _aporte(conta, Decimal(1000))
    _doc(conta, Decimal(1000))
    SchwabStatementImporter(account=conta).import_csv(CSV_COM_PENDENCIA, acknowledge_pending=True)
    with pytest.raises(Exception, match="(?i)pend.ncia de importa"):
        AnnualReconciliationService(2026).run_or_raise()


def test_pendencia_de_ano_anterior_nao_bloqueia_ano_atual(ambiente):
    """Critério é a DATA DO EVENTO, não da pendência: linha de 2025 descoberta
    depois não bloqueia o fechamento de 2026."""
    conta = ambiente
    _aporte(conta, Decimal(1000))
    _doc(conta, Decimal(1000))
    batch = SchwabStatementImporter(account=conta).import_csv(
        "Date,Action,Symbol,Quantity,Price,Amount,Fees\n"
        "12/31/2025,Transfer Out,AAPL,10,0.00,0.00,0.00\n",
        acknowledge_pending=True,
    )
    batch.issues.update(raw_data={"Date": "12/31/2025", "Action": "Transfer Out"})
    AnnualReconciliationService(2026).run_or_raise()  # não levanta


def test_caixa_sem_documento_confirmado_bloqueia(ambiente):
    """Saldo do ledger sem extrato documentado confirmado → pendência, nunca
    passagem automática."""
    conta = ambiente
    _aporte(conta, Decimal(1000))
    with pytest.raises(Exception, match="(?i)saldo documental"):
        AnnualReconciliationService(2026).run_or_raise()


def test_caixa_divergente_bloqueia_com_valores(ambiente):
    conta = ambiente
    _aporte(conta, Decimal(1000))
    _doc(conta, Decimal(999.00))
    with pytest.raises(Exception, match="(?i)1000.00.*999.00|999.00.*1000.00"):
        AnnualReconciliationService(2026).run_or_raise()


def test_caixa_conciliado_passa(ambiente):
    conta = ambiente
    _aporte(conta, Decimal(1000))
    _doc(conta, Decimal(1000))
    AnnualReconciliationService(2026).run_or_raise()  # não levanta


def test_posicao_divergente_bloqueia(ambiente):
    """Posição calculada ≠ documentada em 31/12 → pendência."""
    conta = ambiente
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    _aporte(conta, Decimal(20000))
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="BUY", account=conta, asset=aapl, trade_date=date(2026, 1, 5),
            quantity=Decimal(100), price_usd=Decimal(100),
        ))
    _doc(conta, Decimal(10000), positions=[{"ticker": "AAPL", "quantity": "90"}])
    with pytest.raises(Exception, match="(?i)100.*90|90.*100"):
        AnnualReconciliationService(2026).run_or_raise()


def test_rendimento_sem_estado_de_imposto_exterior_bloqueia(ambiente):
    """'Sem imposto' ≠ retenção zero presumida — exige declaração explícita
    (NO_WITHHOLDING) ou registro do pagamento; UNDECLARED bloqueia."""
    conta = ambiente
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    _aporte(conta, Decimal(20000))
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="BUY", account=conta, asset=aapl, trade_date=date(2026, 1, 5),
            quantity=Decimal(100), price_usd=Decimal(100),
        ))
    _doc(conta, Decimal(10100), positions=[{"ticker": "AAPL", "quantity": "100"}])
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(
            event_type="DIVIDEND", account=conta, asset=aapl,
            trade_date=date(2026, 6, 15), quantity=Decimal(100), per_share_usd=Decimal(1),
        ))
    with pytest.raises(Exception, match="(?i)sem declara..o do estado"):
        AnnualReconciliationService(2026).run_or_raise()
    # declarado explicitamente → passa
    from ledger.models import FinancialEvent
    FinancialEvent.objects.update(foreign_tax_state="NO_WITHHOLDING")
    AnnualReconciliationService(2026).run_or_raise()


def test_revisao_pendente_bloqueia_com_orientacao(ambiente):
    conta = ambiente
    _aporte(conta, Decimal(1000))
    _doc(conta, Decimal(1000))
    from ledger.models import FinancialEvent
    FinancialEvent.objects.create(
        event_type="JUROS", account=conta, trade_date=date(2026, 5, 1),
        amount_usd=Decimal(10), foreign_tax_state="REVIEW_PENDING",
        income_receipt_date=date(2026, 5, 1),
    )
    with pytest.raises(Exception, match="(?i)revis.o"):
        AnnualReconciliationService(2026).run_or_raise()


def test_fechamento_executa_reconciliacao_antes_da_validacao_fiscal(client, ambiente):
    """CloseYearView: reconciliação → validação fiscal → apuração → snapshot.
    Sem saldo documental confirmado, o fechamento falha ANTES de apurar."""
    _aporte(ambiente, Decimal(1000))
    client.post("/apuracao/2026/fechar/")
    from fiscal.models import AnnualAssessment
    assert not AnnualAssessment.objects.filter(year=2026).exists()