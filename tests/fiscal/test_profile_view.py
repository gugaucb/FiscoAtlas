import pytest
from fiscal.models import Profile

pytestmark = pytest.mark.django_db


def test_create_profile_via_form(client):
    resp = client.post("/perfil/", {"name": "Gustavo", "cpf": "000.000.000-00"})
    assert resp.status_code == 302
    assert Profile.objects.count() == 1
    assert b"Gustavo" in client.get("/perfil/").content


def test_update_existing_profile(client):
    Profile.objects.create(name="Velho", cpf="111.111.111-11")
    resp = client.post("/perfil/", {"name": "Novo", "cpf": "222.222.222-22"})
    assert resp.status_code == 302
    assert Profile.objects.count() == 1
    p = Profile.objects.first()
    assert p.name == "Novo" and p.cpf == "222.222.222-22"


def test_form_shows_existing(client):
    Profile.objects.create(name="Gustavo", cpf="000.000.000-00")
    html = client.get("/perfil/").content.decode()
    assert 'value="Gustavo"' in html
