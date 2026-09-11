"""Auditoria-fiscal 07 — CBE v2: caixa real, valor na data-base, 4 datas-base.

Regressões: (1) antes, o caixa somava só aportes/retiradas — uma compra não
reduzia o caixa e o ativo ainda entrava por custo médio, duplicando o valor;
(2) o patrimônio usava custo médio USD como proxy — agora exige valor de
mercado confirmado na data-base (AssetValuation); (3) a obrigação trimestral
era decidida pelo patrimônio de 31/12 — agora cada data-base é apurada
independente (Res. BCB nº 279/2022).
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from fiscal.cbe import CbeService
from fiscal.models import AssetValuation, Profile, TaxRule
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

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
    conta = BrokerAccount.objects.create(broker_name="Avenue", account_number="1")
    return conta


def _evento(conta, **kw):
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        EventService().record(dict(account=conta, **kw))


def _aporte(conta, amount, dia=date(2026, 1, 5)):
    _evento(conta, event_type="APORTE", trade_date=dia, amount_usd=amount)


def _compra(conta, asset, qty, price, dia=date(2026, 1, 5)):
    _evento(conta, event_type="BUY", asset=asset, trade_date=dia,
            quantity=qty, price_usd=price, fee_usd=Decimal(0))


def _valor(conta, asset, valor, dia, confirmed=True):
    return AssetValuation.objects.create(
        account=conta, asset=asset, reference_date=dia, value_usd=valor,
        valuation_method="BROKER_STATEMENT", confirmed=confirmed,
    )


def test_compra_reduz_caixa_e_nao_duplica_patrimonio(ambiente):
    """Regressão (falha no código atual): o caixa antigo somava só
    aportes — US$ 20.000 de aporte + US$ 15.000 de compra davam
    'caixa 20.000 + patrimônio 15.000 = 35.000'. O saldo real de caixa
    após a compra é 5.000; com valor de mercado confirmado, o total é 20.000."""
    conta = ambiente
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    _aporte(conta, Decimal(20000))
    _compra(conta, aapl, Decimal(100), Decimal(150))
    _valor(conta, aapl, Decimal(15000), date(2026, 12, 31))
    r = CbeService(2026).evaluate()
    assert r["annual"]["cash_usd"] == Decimal("5000.00")
    assert r["annual"]["assets_usd"] == Decimal("15000.00")
    assert r["total_usd"] == Decimal("20000.00")
    assert r["status"] == "CBE_UNDETERMINED"  # < 1M e sem completude


def test_sem_valuation_confirmado_fica_undetermined(ambiente):
    """Regressão: antes o patrimônio era qty × custo médio (chute); agora,
    sem valor de mercado confirmado na data-base o item é UNDETERMINED —
    mesmo com caixa alto o suficiente para passar de US$ 1M."""
    conta = ambiente
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    _aporte(conta, Decimal(2000000))
    _compra(conta, aapl, Decimal(500), Decimal(100))
    r = CbeService(2026).evaluate()
    assert r["status"] == "CBE_UNDETERMINED"
    assert r["total_usd"] is None
    pend = r["annual"]["missing_valuations"][0]
    assert pend["asset"].ticker == "AAPL"
    assert pend["quantity"] == Decimal(500)


def test_valuation_nao_confirmado_ignorado(ambiente):
    """Registrado mas NÃO confirmado → não entra; item segue UNDETERMINED."""
    conta = ambiente
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    _aporte(conta, Decimal(2000000))
    _compra(conta, aapl, Decimal(500), Decimal(100))
    _valor(conta, aapl, Decimal(99999), date(2026, 12, 31), confirmed=False)
    r = CbeService(2026).evaluate()
    assert r["status"] == "CBE_UNDETERMINED"
    assert r["total_usd"] is None


def test_valuation_confirmado_usa_valor_de_mercado_na_database(ambiente):
    """Valor patrimonial = valor de mercado CONFIRMADO na data-base — não o
    custo médio (regressão: o código atual usaria qty × custo médio)."""
    conta = ambiente
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    _aporte(conta, Decimal(2000000))
    _compra(conta, aapl, Decimal(500), Decimal(100))  # custo 50.000
    _valor(conta, aapl, Decimal(41000), date(2026, 12, 31))  # mercado ≠ custo
    r = CbeService(2026).evaluate()
    assert r["total_usd"] == Decimal("1991000.00")  # caixa 1.950.000 + mercado 41.000
    assert r["status"] == "CBE_REQUIRED"


def test_ct019_abaixo_do_limite_com_caixa_e_ativo_sem_completude_e_undetermined(ambiente):
    """Total abaixo do limite e sem declaração de completude → indeterminado.
    (Substitui o teste antigo que somava caixa parcial + custo médio —
    a duplicação da compra era o defeito, não o esperado.)"""
    conta = ambiente
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    _aporte(conta, Decimal("199999.80"))
    _compra(conta, aapl, Decimal(100), Decimal("150"))
    _valor(conta, aapl, Decimal("15000.00"), date(2026, 12, 31))
    resultado = CbeService(2026).evaluate()
    assert resultado["status"] == "CBE_UNDETERMINED"
    assert resultado["total_usd"] == Decimal("199999.80")  # caixa real 184.999,80 + mercado 15.000


def test_abaixo_do_limite_com_completude_e_not_required(ambiente):
    conta = ambiente
    _aporte(conta, Decimal("199999.80"))
    Profile.objects.update(external_assets_declared_complete=True)
    resultado = CbeService(2026).evaluate()
    assert resultado["status"] == "CBE_NOT_REQUIRED"


def test_ct020_um_milhao_exige_cbe_anual(ambiente):
    conta = ambiente
    _aporte(conta, Decimal(1000000))
    resultado = CbeService(2026).evaluate()
    assert resultado["status"] == "CBE_REQUIRED"
    assert resultado["annual"]["quarterly"] is False


def test_cem_milhoes_em_31_12_exige_cbe_anual(ambiente):
    """US$ 100M em 31/12 → anual obrigatória; e as datas-base trimestrais
    anteriores (com o mesmo valor) também exigem a trimestral."""
    conta = ambiente
    _aporte(conta, Decimal(100000000))
    resultado = CbeService(2026).evaluate()
    assert resultado["status"] == "CBE_REQUIRED"
    assert resultado["quarterly"] is True


def test_120m_em_31_03_e_80m_em_31_12_trimestral_obrigatoria_anual_nao(ambiente):
    """Regressão cruzada: a obrigação trimestral é decidida PELA data-base
    trimestral — nunca pelo patrimônio de 31/12 (falha no código atual,
    que só olhava 31/12)."""
    conta = ambiente
    _aporte(conta, Decimal(120000000), dia=date(2026, 3, 1))
    _evento(conta, event_type="WITHDRAWAL", trade_date=date(2026, 6, 30),
            amount_usd=Decimal(40000000))
    Profile.objects.update(external_assets_declared_complete=True)
    r = CbeService(2026).evaluate()
    assert r["quarterly_bases"][0]["status"] == "CBE_REQUIRED"      # 31/03 = 120M
    assert r["quarterly_bases"][1]["status"] == "CBE_NOT_REQUIRED"  # 30/06 = 80M
    assert r["quarterly_bases"][2]["status"] == "CBE_NOT_REQUIRED"  # 30/09 = 80M
    assert r["quarterly"] is True                                   # exigível no trimestre
    # 31/12 = 80M: ainda ≥ US$ 1M → anual segue obrigatória (limite anual ≠ trimestral)
    assert r["annual"]["status"] == "CBE_REQUIRED"
    assert r["annual"]["quarterly"] is False
    assert r["total_usd"] == Decimal("80000000.00")


def test_80m_em_31_03_e_120m_em_31_12_apenas_anual_obrigatoria(ambiente):
    conta = ambiente
    _aporte(conta, Decimal(80000000), dia=date(2026, 3, 1))
    _aporte(conta, Decimal(40000000), dia=date(2026, 12, 31))
    Profile.objects.update(external_assets_declared_complete=True)
    r = CbeService(2026).evaluate()
    assert r["quarterly"] is False                                  # 80M < 100M em todas
    assert r["annual"]["status"] == "CBE_REQUIRED"
    assert r["total_usd"] == Decimal("120000000.00")


def test_patrimonio_em_31_12_desconsidera_eventos_do_ano_seguinte(ambiente):
    conta = ambiente
    _aporte(conta, Decimal(2000000), dia=date(2026, 12, 31))
    _aporte(conta, Decimal(5000000), dia=date(2027, 1, 2))
    resultado = CbeService(2026).evaluate()
    assert resultado["total_usd"] == Decimal(2000000)


def test_saldo_negativo_de_caixa_subtrai(ambiente):
    conta = ambiente
    _aporte(conta, Decimal(1000000))
    _evento(conta, event_type="WITHDRAWAL", trade_date=date(2026, 6, 1),
            amount_usd=Decimal(100))
    resultado = CbeService(2026).evaluate()
    assert resultado["total_usd"] == Decimal("999900.00")
    assert resultado["status"] == "CBE_UNDETERMINED"


def test_titularidade_50_na_cbe(ambiente):
    """Auditoria-fiscal 06 aplicada à CBE: valores atribuíveis respeitam a
    participação do titular — conta 50% com US$ 2M → US$ 1M atribuído."""
    conta = ambiente
    conta.ownership_share = Decimal("50.00")
    conta.save()
    _aporte(conta, Decimal(2000000))
    r = CbeService(2026).evaluate()
    assert r["annual"]["cash_usd"] == Decimal("1000000.00")
    assert r["status"] == "CBE_REQUIRED"


def test_cbe_aparece_no_relatorio(ambiente):
    from fiscal.report import ReportService
    conta = ambiente
    _aporte(conta, Decimal(1000000))
    with mock.patch("fx.service.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        report = ReportService(2026).build()
    assert report["cbe"]["status"] == "CBE_REQUIRED"