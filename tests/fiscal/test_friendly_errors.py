import pytest
from fiscal.models import TaxRule

pytestmark = pytest.mark.django_db


@pytest.fixture
def rule(db):
    TaxRule.objects.create(tax_year=2026, rule_version="V2",
                           brackets=[{"limit_brl": None, "rate": "0.15"}],
                           confirmed=True, effective_from="2026-01-01", effective_until="2026-12-31")


def test_report_shows_friendly_error_without_ptax(client, rule, monkeypatch):
    from fx.service import PtaxService
    from unittest import mock
    with mock.patch.object(PtaxService, "get_rate", side_effect=ValueError("PTAX indisponível para 31/12/2026")):
        resp = client.get("/relatorio/2026/")
    assert resp.status_code == 200
    html = resp.content.decode()
    # contrato novo: form inline de PTAX de fechamento em vez de erro genérico
    assert "PTAX de fechamento" in html
    assert "fechamentoptax" in html  # link para o BCB
    assert "Traceback" not in html


def test_memoria_pdf_shows_friendly_error(client, rule, monkeypatch):
    from fiscal.memoria import build_memoria
    from unittest import mock
    with mock.patch("fiscal.views.build_memoria", side_effect=ValueError("PTAX indisponível")):
        resp = client.get("/relatorio/2026/memoria-pdf")
    assert resp.status_code == 200
    assert b"Traceback" not in resp.content
