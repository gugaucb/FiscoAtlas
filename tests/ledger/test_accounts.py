import pytest
from ledger.models import BrokerAccount

pytestmark = pytest.mark.django_db


@pytest.fixture
def acct(db):
    return BrokerAccount.objects.create(broker_name="Avenue Securities", account_number="1")


def test_criar_conta_com_apelido(client):
    resp = client.post("/contas/", {
        "name": "Corrente Avenue", "broker_name": "Avenue Securities",
        "account_number": "777", "account_type": "CASH", "is_interest_bearing": "false",
    })
    assert resp.status_code == 302
    acct = BrokerAccount.objects.get(account_number="777")
    assert acct.name == "Corrente Avenue"


def test_apelido_aparece_no_lancamento_e_caixa(client, acct):
    acct.name = "Investimento"
    acct.save()
    html = client.get("/eventos/novo/").content.decode()
    assert "Investimento" in html
    html = client.get("/caixa/").content.decode()
    assert "Investimento" in html


def test_sem_apelido_usa_corretora(client, acct):
    html = client.get("/caixa/").content.decode()
    assert "Avenue Securities" in html


def test_editar_conta(client, acct):
    resp = client.post(f"/contas/{acct.pk}/", {
        "name": "Novo nome", "broker_name": acct.broker_name,
        "account_number": acct.account_number, "account_type": "CUSTODY",
        "is_interest_bearing": "true",
    })
    assert resp.status_code == 302
    acct.refresh_from_db()
    assert acct.name == "Novo nome"
    assert acct.account_type == "CUSTODY"
    assert acct.is_interest_bearing is True


def test_desativar_conta(client, acct):
    resp = client.post(f"/contas/{acct.pk}/desativar/")
    assert resp.status_code == 302
    acct.refresh_from_db()
    assert acct.active is False
    # sai do select de novos lançamentos
    html = client.get("/eventos/novo/").content.decode()
    assert f'value="{acct.pk}"' not in html
    # permanece na tela de caixa
    html = client.get("/caixa/").content.decode()
    assert acct.broker_name in html


def test_juros_em_conta_nao_remunerada_mensagem_amigavel(client, acct):
    with __import__("unittest").mock.patch(
        "ledger.views.EventService._ptax_rate", return_value=__import__("decimal").Decimal("5")
    ):
        resp = client.post("/eventos/novo/", {
            "event_type": "JUROS", "account": acct.pk,
            "trade_date": "2026-03-01", "amount_usd": "10",
        })
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "remunerada" in html
    assert "Traceback" not in html
    # dados preservados
    assert 'value="10"' in html or ">10<" in html


def test_selo_variacao_cambial_isenta(client, db):
    nao_remun = BrokerAccount.objects.create(broker_name="A", account_number="1", is_interest_bearing=False)
    remun = BrokerAccount.objects.create(broker_name="B", account_number="2", is_interest_bearing=True)
    html = client.get("/caixa/").content.decode()
    assert "variação cambial isenta" in html
    assert "remunerada" in html
