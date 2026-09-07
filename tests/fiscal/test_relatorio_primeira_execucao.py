"""Cenário do usuário: banco NOVO (sem TaxRule) no Docker — informar PTAX
de 31/12 pelo Relatório deve renderizar o relatório, não estourar TaxRule."""
from datetime import date
from unittest import mock

import httpx
import pytest

from fiscal.management.commands.seed_tax_rules import Command as SeedCommand
from fx.service import PtaxService

pytestmark = pytest.mark.django_db

INDISPONIVEL = httpx.HTTPStatusError("500", request=mock.Mock(), response=mock.Mock())


@pytest.fixture
def banco_novo_sem_regras(residente):
    """Simula o primeiro boot do Docker: nenhuma TaxRule no banco."""
    from fiscal.models import TaxRule
    TaxRule.objects.all().delete()
    with mock.patch.object(PtaxService, "_fetch_bcb", side_effect=INDISPONIVEL):
        yield


def test_informar_ptax_em_banco_novo_renderiza_relatorio(client, banco_novo_sem_regras):
    # primeiro boot do container: entrypoint roda migrate + seed
    SeedCommand().handle()

    # 1º acesso: form de PTAX aparece
    resp = client.get("/relatorio/2026/")
    assert "PTAX de fechamento" in resp.content.decode()

    # usuário informa a PTAX
    resp = client.post("/relatorio/2026/ptax-fechamento/", {"rate": "5.42", "motivo": "primeira execução"})
    assert resp.status_code == 302

    # BUG relatado: aqui vinha "Sem TaxRule confirmada para o ano 2026"
    resp = client.get("/relatorio/2026/")
    corpo = resp.content.decode()
    assert "Sem TaxRule" not in corpo, "relatório travou na TaxRule mesmo com PTAX informada"
    assert "5.42" in corpo or "5,42" in corpo


def test_seed_cria_v2_confirmada_idempotente(banco_novo_sem_regras):
    SeedCommand().handle()
    from fiscal.models import TaxRule
    v2 = TaxRule.objects.get(tax_year=2026, rule_version="V2")
    assert v2.confirmed is True
    assert v2.brackets == [{"limit_brl": None, "rate": "0.15"}]

    # idempotente: rodar de novo não duplica nem altera
    SeedCommand().handle()
    assert TaxRule.objects.filter(tax_year=2026).count() == 2
    assert TaxRule.objects.get(tax_year=2026, rule_version="V2").confirmed is True


def test_seed_nao_desconfirma_v2_existente_confirmada(banco_novo_sem_regras):
    from fiscal.models import TaxRule
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2", brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, effective_from=date(2026, 1, 1), notes="minha regra",
    )
    SeedCommand().handle()
    assert TaxRule.objects.get(tax_year=2026, rule_version="V2").confirmed is True
