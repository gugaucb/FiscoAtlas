"""Achado P1 do auditor (18): quantidade documentada validada na fronteira.

O formulário aceitava "AAPL, abc" (só checava texto após a vírgula) e
gravava a string; a reconciliação faz Decimal(str(...)) durante o
fechamento e quebrava com InvalidOperation — crash, não pendência
com mensagem clara."""
from decimal import Decimal

import pytest

from fiscal.reconciliation_forms import DocumentedBalanceForm
from ledger.models import BrokerAccount, DocumentedBalance

pytestmark = pytest.mark.django_db


@pytest.fixture
def conta(db):
    return BrokerAccount.objects.create(broker_name="Avenue", account_number="1")


def _form(conta, positions_text):
    return DocumentedBalanceForm(data={
        "account": conta.pk,
        "reference_date": "2026-12-31",
        "cash_usd": "1000.00",
        "confirmed": "on",
        "positions_text": positions_text,
    })


def test_quantidade_nao_numerica_rejeitada_no_formulario(conta):
    """Falha no código atual: 'AAPL, abc' era aceito e quebrava o fechamento."""
    form = _form(conta, "AAPL, abc")
    assert not form.is_valid()
    assert "não é um número" in " ".join(form.errors["positions_text"])
    assert not DocumentedBalanceForm._meta.model.objects.filter(account=conta).exists()


def test_quantidade_negativa_rejeitada(conta):
    form = _form(conta, "AAPL, -5")
    assert not form.is_valid()
    assert "não pode ser negativa" in " ".join(form.errors["positions_text"])


def test_ticker_duplicado_rejeitado(conta):
    """Duplicado era aceito e sobrescrevia em silêncio no confronto."""
    form = _form(conta, "AAPL, 10\nAAPL, 20")
    assert not form.is_valid()
    assert "Ticker duplicado" in " ".join(form.errors["positions_text"])


def test_quantidade_valida_gravada_como_decimal(conta):
    """Converte para Decimal na fronteira (validação); grava string numérica
    (positions é JSONField) que a reconciliação consome com Decimal(str())."""
    form = _form(conta, "AAPL, 150.5")
    assert form.is_valid(), form.errors
    instancia = form.save()
    assert instancia.positions == [{"ticker": "AAPL", "quantity": "150.5"}]


def test_reconciliacao_nao_quebra_com_valor_gravado_pelo_formulario(conta):
    """End-to-end: formulário válido → reconciliação consome a quantidade
    gravada sem InvalidOperation; divergência vira pendência com valores."""
    from fiscal.reconciliation import AnnualReconciliationService
    from ledger.models import Asset, OpeningPosition
    form = _form(conta, "AAPL, 150")
    assert form.is_valid()
    form.save()
    aapl = Asset.objects.create(ticker="AAPL", description="Apple", asset_type="FOREIGN_EQUITY")
    OpeningPosition.objects.create(
        account=conta, asset=aapl, reference_date="2025-12-31",
        quantity=Decimal("100"), total_cost_brl=Decimal("1000"),
    )
    # posição documentada 150 ≠ calculada 100 → pendência, não crash
    with pytest.raises(Exception, match="(?i)100.*150|150.*100"):
        AnnualReconciliationService(2026).run_or_raise()