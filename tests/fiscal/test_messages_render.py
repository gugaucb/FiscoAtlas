"""Mensagens do Django devem renderizar na UI (bug do smoke do manual).

O CloseYearView reporta o resultado via messages.success/error, mas sem o
context processor django.contrib.messages.context_processors.messages o
`{% if messages %}` do base.html nunca rende — o usuário não vê NENHUMA
mensagem de sucesso ou erro em tela nenhuma.
"""
import pytest

from datetime import date

from fiscal.models import TaxRule

pytestmark = pytest.mark.django_db


@pytest.fixture
def regra_confirmada(db):
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, quote_type="VENDA", date_rule="INCOME_RECEIPT_DATE",
        effective_from=date(2026, 1, 1),
    )


def test_sucesso_do_fechamento_aparece_na_tela(client, residente, regra_confirmada):
    # fechamento válido → mensagem de sucesso deve renderizar
    resp = client.post("/apuracao/2026/fechar/")
    assert resp.status_code == 302
    resp = client.get("/apuracao/2026/")
    html = resp.content.decode()
    assert 'ul class="messages"' in html
    assert "fechado" in html.lower()
