"""Auditoria-fiscal 13 — suíte adversarial de regressão fiscal.

Matriz de cenários da auditoria contábil: cada teste tem VALORES ESPERADOS
calculados à mão (nunca comparação método-a-método) e documenta a qual
correção do backlog corresponde e por que o comportamento anterior estava
errado. Regra de ouro: valores fiscais incorretos não são mantidos — o
teste é substituído com a documentação do porquê.

| Cenário                                    | Correção |
|--------------------------------------------|----------|
| Duas corretoras, mesmo ativo               | 03       |
| Posição de abertura por conta (constraint) | 03       |
| CSV com SELL                               | 01       |
| CSV com evento desconhecido                | 01       |
| CBE 4 datas-base                           | 07       |
| Perda 2.000 → uso 1.000 → refechar         | 09       |
| Conta 50%                                  | 06       |
| Retenção exterior 30%                      | 05       |
| DARF 9,99 / 99 / 100 / 300                 | 08       |
| Trade 31/12 / recebimento 02/01            | 10       |
| 2 pagamentos no mesmo rendimento           | 04       |
| Imposto exterior UNKNOWN                   | 05/12    |
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from fiscal.cbe import CbeService
from fiscal.darf import DarfGuideService
from fiscal.engine import TaxEngine
from fiscal.losses import LossLedgerService
from fiscal.models import FilingRule, TaxRule
from fiscal.validator import AnnualClosingValidator
from ledger.importers.schwab import SchwabStatementImporter
from ledger.models import (
    Asset, BrokerAccount, FinancialEvent, ForeignTaxPayment, OpeningPosition,
)
from ledger.position import PositionService
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


def _evento(conta, **kw):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        return EventService().record(dict(account=conta, **kw))


def _compute(engine):
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        return engine.compute()


# ---------------------------------------------------------------- 03
def test_duas_corretoras_mesmo_ativo_custos_independentes(db, residente):
    """Correção 03: _opening ignorava a conta — Avenue(100) e Schwab(50) de
    AAPL viravam 150 em qualquer corretora. Agora cada conta tem posição e
    custo próprios (adversarial do auditor: 100/50.000 e 50/40.000)."""
    avenue = BrokerAccount.objects.create(broker_name="Avenue", account_number="A1")
    schwab = BrokerAccount.objects.create(broker_name="Schwab", account_number="S1")
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    OpeningPosition.objects.create(account=avenue, asset=aapl, quantity=Decimal(100), total_cost_brl=Decimal(50000))
    OpeningPosition.objects.create(account=schwab, asset=aapl, quantity=Decimal(50), total_cost_brl=Decimal(40000))
    pos_avenue = PositionService().position(avenue, aapl)
    pos_schwab = PositionService().position(schwab, aapl)
    assert (pos_avenue["quantity"], pos_avenue["cost_brl_total"]) == (Decimal(100), Decimal(50000))
    assert (pos_schwab["quantity"], pos_schwab["cost_brl_total"]) == (Decimal(50), Decimal(40000))
    # NUNCA 150 nem 90.000 numa conta só
    assert pos_avenue["quantity"] + pos_schwab["quantity"] == Decimal(150)
    assert pos_avenue["cost_brl_total"] != pos_schwab["cost_brl_total"]


def test_abertura_duplicada_mesma_conta_data_violada(db, residente):
    """Correção 03: constraint uniq(account, asset, reference_date) — sem ela,
    uma segunda abertura somava ao custo sem rastro."""
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="A1")
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    OpeningPosition.objects.create(account=conta, asset=aapl, quantity=Decimal(10), total_cost_brl=Decimal(1000))
    with pytest.raises(IntegrityError):
        OpeningPosition.objects.create(account=conta, asset=aapl, quantity=Decimal(5), total_cost_brl=Decimal(500))


# ---------------------------------------------------------------- 01
CSV_SELL = (
    "Date,Action,Symbol,Quantity,Price,Amount,Fees\n"
    "06/01/2026,Sell,AAPL,10,110.00,1100.00,1.00\n"
)
CSV_DESCONHECIDO = (
    "Date,Action,Symbol,Quantity,Price,Amount,Fees\n"
    "06/01/2026,Journal,AAPL,10,110.00,1100.00,0.00\n"
)


def test_csv_com_sell_e_importado_como_venda(ambiente):
    """Correção 01: antes, `Sell` caía no `continue` silencioso do
    ACTION_MAP.get(action) e a venda desaparecia do ledger."""
    conta = ambiente
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    OpeningPosition.objects.create(account=conta, asset=aapl, quantity=Decimal(100), total_cost_brl=Decimal(10000))
    batch = SchwabStatementImporter(account=conta).import_csv(CSV_SELL)
    assert batch.rows_imported == 1
    ev = FinancialEvent.objects.get(event_type="SELL")
    assert ev.quantity == Decimal(10)
    assert ev.price_usd == Decimal(110)


def test_csv_evento_desconhecido_vira_pendencia_visivel(ambiente):
    """Correção 01: 'Journal' não pode desaparecer — vira ImportIssue PENDING
    e o lote só concilia com ela contabilizada (rows_source = importadas +
    pendências + ignoradas confirmadas)."""
    conta = ambiente
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    OpeningPosition.objects.create(account=conta, asset=aapl, quantity=Decimal(100), total_cost_brl=Decimal(10000))
    batch = SchwabStatementImporter(account=conta).import_csv(CSV_DESCONHECIDO, acknowledge_pending=True)
    assert batch.rows_unsupported == 1
    issue = batch.issues.get()
    assert issue.status == "PENDING"
    assert issue.raw_action == "Journal"


# ---------------------------------------------------------------- 07
def test_cbe_quatro_datas_base_independentes(ambiente):
    """Correção 07: antes só 31/12 era apurado e decidia a trimestral.
    US$ 120M em 31/03; retirada em 30/06 → 80M: cada data-base tem o próprio
    status (completude declarada para eliminar a indeterminação)."""
    from fiscal.models import Profile
    Profile.objects.update(external_assets_declared_complete=True)
    conta = ambiente
    _evento(conta, event_type="APORTE", trade_date=date(2026, 3, 20), amount_usd=Decimal(120000000))
    _evento(conta, event_type="WITHDRAWAL", trade_date=date(2026, 6, 30), amount_usd=Decimal(40000000))
    r = CbeService(2026).evaluate()
    bases = {(t["data_base"].month, t["data_base"].day): t for t in r["quarterly_bases"]}
    assert bases[(3, 31)]["total_usd"] == Decimal("120000000.00")
    assert bases[(3, 31)]["status"] == "CBE_REQUIRED"
    assert bases[(6, 30)]["total_usd"] == Decimal("80000000.00")
    assert bases[(6, 30)]["status"] == "CBE_NOT_REQUIRED"
    assert bases[(9, 30)]["total_usd"] == Decimal("80000000.00")
    assert bases[(9, 30)]["status"] == "CBE_NOT_REQUIRED"
    # 31/12 = 80M ≥ US$ 1M → anual obrigatória (limite anual ≠ trimestral)
    assert r["annual"]["total_usd"] == Decimal("80000000.00")
    assert r["annual"]["status"] == "CBE_REQUIRED"


# ---------------------------------------------------------------- 09
def test_perda_2000_uso_1000_refechar_saldo_1000(db, residente):
    """Correção 09: apply_compensation apagava as compensações sem DEVOLVER
    ao registro — refechar zerava o saldo consumido. Agora: perda 2.000,
    rendimento 1.000 → saldo 1.000; refechar mantém 1.000 (não 2.000, não 0)."""
    LossLedgerService.record_loss(2024, Decimal(2000))
    consumido = LossLedgerService.apply_compensation(2025, Decimal(1000))
    assert consumido == Decimal("1000.00")
    assert LossLedgerService.open_records(2025)[0].remaining_brl == Decimal("1000.00")
    # refechamento idempotente
    LossLedgerService.apply_compensation(2025, Decimal(1000))
    assert LossLedgerService.open_records(2025)[0].remaining_brl == Decimal("1000.00")


# ---------------------------------------------------------------- 06
def test_conta_50_por_cento_rendimento_e_imposto_na_metade(ambiente):
    """Correção 06: o engine tributava o valor INTEGRAL e só o relatório
    dividia por fatia depois. Agora o CÁLCULO usa OwnershipService:
    dividendo bruto US$ 1.000 × 5 = R$ 5.000 → 50% = R$ 2.500; IR 15% = 375."""
    conta = ambiente
    conta.ownership_share = Decimal("50.00")
    conta.save()
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    _evento(conta, event_type="DIVIDEND", asset=aapl, trade_date=date(2026, 6, 15),
            quantity=Decimal(100), per_share_usd=Decimal(10))
    r = _compute(TaxEngine(2026))
    assert r["income_brl"] == Decimal("2500.00")
    assert r["tax_brl"] == Decimal("375.00")
    assert r["tax_due_brl"] == Decimal("375.00")


# ---------------------------------------------------------------- 05
def test_retencao_30_por_cento_nao_bloqueia_e_credito_limitado(ambiente):
    """Correção 05: retenção de 30% dos EUA é legítima — antes era ERRO
    bloqueante no fechamento. Agora o fechamento passa e o crédito fica
    limitado a 15%: bruto R$ 5.000 → limite 750; pago 30 USD × 5 = 150 →
    usa os 150 integralmente (pago < limite); retenção maior que o IR do
    rendimento é que seria parcialmente não aproveitada."""
    conta = ambiente
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    _evento(conta, event_type="DIVIDEND", asset=aapl, trade_date=date(2026, 6, 15),
            quantity=Decimal(100), per_share_usd=Decimal(10), tax_usd=Decimal(30),
            foreign_tax_payment_date=date(2026, 6, 15), date_evidence_source="BROKER_STATEMENT",
            country_code="US", jurisdiction_level="FEDERAL", tax_type="WITHHOLDING_INCOME_TAX")
    r = _compute(TaxEngine(2026))
    assert r["withholding_credit_brl"] == Decimal("150.00")  # pago 150 < limite 750
    assert r["tax_brl"] == Decimal("750.00")
    assert r["tax_due_brl"] == Decimal("600.00")
    AnnualClosingValidator(2026).validate_or_raise()          # fechamento PASSA


# ---------------------------------------------------------------- 08
@pytest.fixture
def regra_darf(db, residente):
    return FilingRule.objects.create(
        filing_year=2027, rule_version="DARF/2027-v1",
        due_date=date(2027, 4, 30), darf_code="0211",
        minimum_darf=Decimal(10), minimum_installment=Decimal(100),
        minimum_tax_for_installment=Decimal(100), maximum_installments=8,
        is_homologated=True,
    )


def test_darf_999_adiamento_nao_extincao(regra_darf):
    """Correção 08 (ticket 02/08): R$ 9,99 não é 'imposto extinto' nem
    'dispensado' — é ADIAMENTO com acúmulo (art. 938, §§4º e 5º, RIR/2018)."""
    guia = DarfGuideService(2026).build(tax_due_brl=Decimal("9.99"))
    assert guia["adiado"] is True
    assert guia["payment_required_now"] is False
    assert "art. 938, § 4º" in guia["mensagem"]
    assert "art. 938, § 5º" in guia["mensagem"]
    assert "permanece devido" in guia["mensagem"]


def test_darf_99_quota_unica(regra_darf):
    """Correção 08: 99 < quota mínima 100 → quota única de 99 (antes
    dividia por 8 = 12,375, abaixo do mínimo legal)."""
    guia = DarfGuideService(2026).build(tax_due_brl=Decimal(99))
    assert guia["parcelamento"]["n_quotas"] == 1
    assert guia["parcelamento"]["valor_quota"] == Decimal("99.00")


def test_darf_100_respeita_minimo_de_quota(regra_darf):
    """Correção 08: 100/8 = 12,50 < 100 → desce até 1 quota de 100."""
    guia = DarfGuideService(2026).build(tax_due_brl=Decimal(100))
    assert guia["parcelamento"]["n_quotas"] == 1
    assert guia["parcelamento"]["valor_quota"] == Decimal("100.00")


def test_darf_300_tres_quotas_validas(regra_darf):
    """Correção 08: 300/8 = 37,50 < 100 → 3 quotas de 100 (máximo possível
    que respeita o mínimo, NÃO divisão automática por 8)."""
    guia = DarfGuideService(2026).build(tax_due_brl=Decimal(300))
    assert guia["parcelamento"]["n_quotas"] == 3
    assert guia["parcelamento"]["valor_quota"] == Decimal("100.00")


# ---------------------------------------------------------------- 10
def test_trade_3112_recebimento_0201_ano_do_recebimento(ambiente):
    """Correção 10: dividendo negociado 31/12/2026, creditado 02/01/2027 —
    o ano fiscal é o do RECEBIMENTO (antes: ano da operação, 2026)."""
    conta = ambiente
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    TaxRule.objects.create(
        tax_year=2027, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, effective_from=date(2027, 1, 1),
    )
    _evento(conta, event_type="DIVIDEND", asset=aapl, trade_date=date(2026, 12, 31),
            quantity=Decimal(100), per_share_usd=Decimal(1), income_receipt_date=date(2027, 1, 2))
    assert _compute(TaxEngine(2026))["income_brl"] == Decimal("0.00")
    assert _compute(TaxEngine(2027))["income_brl"] == Decimal("500.00")


# ---------------------------------------------------------------- 04
def test_dois_pagamentos_de_imposto_no_mesmo_rendimento(ambiente):
    """Correção 04: o mapa event_id→pagamento guardava UM pagamento — o
    segundo (ex.: retenção estadual) desaparecia do cálculo. Federal 15
    (elegível) + estadual 5 (inelegível): gross = 985 + 20 = 1.005 USD →
    R$ 5.025,00; crédito federal 75; estadual segregado como não elegível."""
    conta = ambiente
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    ev = _evento(conta, event_type="DIVIDEND", asset=aapl, trade_date=date(2026, 6, 15),
                 quantity=Decimal(100), per_share_usd=Decimal(10), tax_usd=Decimal(15),
                 foreign_tax_payment_date=date(2026, 6, 15), date_evidence_source="BROKER_STATEMENT",
                 country_code="US", jurisdiction_level="FEDERAL", tax_type="WITHHOLDING_INCOME_TAX")
    ForeignTaxPayment.objects.create(
        financial_event=ev, tax_usd=Decimal(5),
        foreign_tax_payment_date=date(2026, 6, 15), country_code="US",
        jurisdiction_level="STATE", tax_type="WITHHOLDING_INCOME_TAX",
        capture_method="MANUAL", date_evidence_source="BROKER_STATEMENT",
    )
    r = _compute(TaxEngine(2026))
    assert r["income_brl"] == Decimal("5025.00")          # bruto inclui AMBOS os pagamentos
    assert r["withholding_credit_brl"] == Decimal("75.00")  # só o federal (15×5)
    assert r["ineligible_foreign_tax_brl"] == Decimal("25.00")  # estadual (5×5)


# ---------------------------------------------------------------- 05/12
def test_imposto_exterior_unknown_bloqueia_fechamento_ate_classificar(ambiente):
    """Correção 05/12: pagamento com fatos UNKNOWN não tem regra fiscal
    silenciosa — crédito zero e FECHAMENTO BLOQUEADO com orientação."""
    conta = ambiente
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    _evento(conta, event_type="DIVIDEND", asset=aapl, trade_date=date(2026, 6, 15),
            quantity=Decimal(100), per_share_usd=Decimal(10), tax_usd=Decimal(30),
            foreign_tax_payment_date=date(2026, 6, 15), date_evidence_source="BROKER_STATEMENT",
            country_code="US")  # jurisdiction_level/tax_type UNKNOWN (defaults)
    r = _compute(TaxEngine(2026))
    assert r["withholding_credit_brl"] == Decimal("0.00")
    with pytest.raises(ValidationError, match="(?i)classifique"):
        AnnualClosingValidator(2026).validate_or_raise()