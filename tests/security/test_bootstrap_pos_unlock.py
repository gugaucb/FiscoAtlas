"""Autocorreção pós-desbloqueio: migrations + seed rodam no primeiro unlock."""
import datetime
from unittest import mock

from django.conf import settings

import pytest

from fiscal.models import TaxRule
from security import bootstrap
from security.bootstrap import bootstrap_pos_unlock

pytestmark = pytest.mark.django_db(databases=["default", "vault"])


@pytest.fixture(autouse=True)
def reseta_flag():
    bootstrap._done = False
    yield
    bootstrap._done = False


@pytest.fixture
def v2_confirmada():
    regra, _ = TaxRule.objects.update_or_create(
        tax_year=2026, rule_version="V2",
        defaults={
            "confirmed": True,
            "brackets": [{"limit_brl": None, "rate": "0.15"}],
            "effective_from": datetime.date(2026, 1, 1),
        },
    )
    return regra


def test_rodar_migrate_e_seed_uma_vez():
    with mock.patch.object(settings, "SECURITY_VAULT_ALIAS", "vault"), \
             mock.patch("django.core.management.call_command") as cc:
        assert bootstrap_pos_unlock() is True
        assert bootstrap_pos_unlock() is False  # segunda chamada é no-op
        nomes = [c.args[0] for c in cc.call_args_list]
        assert nomes == ["migrate", "migrate", "seed_tax_rules"]


def test_migrate_vault_com_alias_vault():
    with mock.patch.object(settings, "SECURITY_VAULT_ALIAS", "vault"), \
             mock.patch("django.core.management.call_command") as cc:
        bootstrap_pos_unlock()
        vault_call = cc.call_args_list[1]
        assert vault_call.kwargs.get("database") == "vault"


def test_seed_nao_desconfirma_v2_confirmada(v2_confirmada):
    with mock.patch.object(settings, "SECURITY_VAULT_ALIAS", "vault"):
        bootstrap_pos_unlock()
    assert TaxRule.objects.get(tax_year=2026, rule_version="V2").confirmed is True
