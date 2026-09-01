import pytest
from ledger.models import BrokerAccount, FinancialEvent

pytestmark = pytest.mark.django_db


@pytest.fixture
def account():
    return BrokerAccount.objects.create(broker_name="Avenue", account_number="123", country_code="US")


@pytest.fixture(autouse=True)
def _bcb_fora(monkeypatch):
    """API do BCB indisponível durante todos estes testes."""
    from fx.service import PtaxService

    def boom(self, day):
        import httpx

        raise httpx.ConnectError("BCB off")

    monkeypatch.setattr(PtaxService, "_fetch_bcb", boom)


def _payload(account, **kw):
    base = {"event_type": "APORTE", "account": account.pk, "trade_date": "2026-01-15",
            "amount_usd": "1000"}
    base.update(kw)
    return base


def test_evento_com_ptax_manual_mesmo_sem_api(client, account):
    resp = client.post("/eventos/novo/", _payload(account, ptax_manual="5.4321", ptax_reason="API fora"))
    assert resp.status_code == 302
    ev = FinancialEvent.objects.get()
    assert str(ev.fx_rate) == "5.43210000"
    assert ev.amount_brl == pytest.approx(__import__("decimal").Decimal("5432.1"), abs=__import__("decimal").Decimal("0.01"))
    rate = ev  # conferir PtaxRate persistido como override
    from fx.models import PtaxRate
    pr = PtaxRate.objects.get(requested_date="2026-01-15", manually_overridden=True)
    assert pr.rate == __import__("decimal").Decimal("5.4321")
    assert pr.override_reason == "API fora"


def test_ptax_manual_sem_motivo_rejeitado(client, account):
    resp = client.post("/eventos/novo/", _payload(account, ptax_manual="5.4321"))
    assert resp.status_code == 200  # form re-renderizado com erro
    assert not FinancialEvent.objects.exists()
    assert "motivo" in resp.content.decode().lower()


def test_sem_manual_e_sem_api_mensagem_amigavel(client, account):
    resp = client.post("/eventos/novo/", _payload(account))
    assert resp.status_code == 200
    page = resp.content.decode()
    assert not FinancialEvent.objects.exists()
    assert "manual" in page.lower()


def test_form_mostra_link_bcb(client, account):
    resp = client.get("/eventos/novo/")
    assert "bcb.gov.br" in resp.content.decode()
    assert "fechamentoptax" in resp.content.decode()
