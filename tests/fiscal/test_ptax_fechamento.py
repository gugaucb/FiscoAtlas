"""PTAX de fechamento (31/12) manual na aba Relatório."""
from datetime import date
from decimal import Decimal
from unittest import mock

import httpx
import pytest

from fx.models import PtaxRate
from fx.service import PtaxService

INDISPONIVEL = httpx.HTTPStatusError("500", request=mock.Mock(), response=mock.Mock())


@pytest.fixture
def sem_ptax_bcb():
    with mock.patch.object(PtaxService, "_fetch_bcb", side_effect=INDISPONIVEL):
        yield


@pytest.fixture
def regra_2026(db):
    from fiscal.models import TaxRule

    TaxRule.objects.get_or_create(
        tax_year=2026, rule_version="t-v1",
        defaults={
            "brackets": [{"limit_brl": None, "rate": "0.15"}],
            "confirmed": True, "effective_from": date(2026, 1, 1),
        },
    )


@pytest.mark.django_db
def test_relatorio_com_ptax_futura_mostra_form_inline(client, sem_ptax_bcb, regra_2026):
    resp = client.get("/relatorio/2026/")
    body = resp.content.decode()
    assert "PTAX de fechamento" in body
    assert 'name="rate"' in body and 'name="motivo"' in body
    assert "página de erro" not in body


@pytest.mark.django_db
def test_post_registra_override_e_renderiza_relatorio(client, sem_ptax_bcb, regra_2026):
    resp = client.post("/relatorio/2026/ptax-fechamento/", {"rate": "5.42", "motivo": "fechamento estimado"})
    assert resp.status_code == 302
    reg = PtaxRate.objects.get(requested_date=date(2026, 12, 31))
    assert reg.manually_overridden is True
    assert reg.rate == Decimal("5.42")
    assert reg.override_reason == "fechamento estimado"

    page = client.get("/relatorio/2026/").content.decode()
    assert "PTAX de fechamento" not in page  # form some depois de registrado
    assert "5.42" in page or "5,42" in page


@pytest.mark.django_db
def test_post_sem_motivo_nao_grava(client, sem_ptax_bcb, regra_2026):
    resp = client.post("/relatorio/2026/ptax-fechamento/", {"rate": "5.42", "motivo": "  "})
    assert resp.status_code == 200
    assert "motivo" in resp.content.decode().lower()
    assert not PtaxRate.objects.filter(requested_date=date(2026, 12, 31)).exists()


@pytest.mark.django_db
def test_relatorio_com_ptax_em_cache_nao_mostra_form(client, regra_2026):
    PtaxRate.objects.create(
        requested_date=date(2026, 12, 31), effective_date=date(2026, 12, 31),
        rate=Decimal("5.4000"),
    )
    page = client.get("/relatorio/2026/").content.decode()
    assert "PTAX de fechamento" not in page
    assert "5.4000" in page or "5,40" in page
