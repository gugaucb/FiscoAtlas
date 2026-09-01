"""Editar a PTAX de 31/12 no Relatório (override vigente pode ser alterado)."""
from datetime import date
from decimal import Decimal
from unittest import mock

import httpx
import pytest

from fiscal.management.commands.seed_tax_rules import Command as SeedCommand
from fx.models import PtaxRate
from fx.service import PtaxService

pytestmark = pytest.mark.django_db

INDISPONIVEL = httpx.HTTPStatusError("500", request=mock.Mock(), response=mock.Mock())


@pytest.fixture
def ambiente():
    SeedCommand().handle()
    with mock.patch.object(PtaxService, "_fetch_bcb", side_effect=INDISPONIVEL):
        yield


def _desbloqueia(client):
    from security.vault import VaultService

    VaultService().setup("senha-teste-123") if not VaultService().is_configured() else None
    client.post("/bloqueado/", {"password": "senha-teste-123"})


def test_get_com_ptax_editar_mostra_form_preenchido(client, ambiente):
    _desbloqueia(client)
    client.post("/relatorio/2026/ptax-fechamento/", {"rate": "5.42", "motivo": "inicial"})
    resp = client.get("/relatorio/2026/?ptax=editar")
    corpo = resp.content.decode()
    assert "PTAX de fechamento" in corpo
    assert "5.42" in corpo  # valor vigente pré-preenchido
    assert "Relatório DIRPF" in corpo  # relatório continua renderizando


def test_novo_override_prevalece_sobre_o_anterior(client, ambiente):
    PtaxService().override(date(2026, 12, 31), Decimal("5.42"), "inicial")
    PtaxService().override(date(2026, 12, 31), Decimal("5.60"), "correção")
    assert PtaxService().get_rate(date(2026, 12, 31)).rate == Decimal("5.60")


def test_salvar_edicao_atualiza_relatorio(client, ambiente):
    _desbloqueia(client)
    client.post("/relatorio/2026/ptax-fechamento/", {"rate": "5.42", "motivo": "inicial"})
    resp = client.post("/relatorio/2026/ptax-fechamento/", {"rate": "5.60", "motivo": "correção"})
    assert resp.status_code == 302
    corpo = client.get("/relatorio/2026/").content.decode()
    assert "5,60000000" in corpo or "5.60" in corpo
    assert "PTAX de fechamento" not in corpo  # sem ?ptax=editar o form fica fechado
