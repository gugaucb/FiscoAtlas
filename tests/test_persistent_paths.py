"""Caminhos persistentes configuráveis por env (Docker)."""
import importlib
import os
from unittest import mock

import django
import pytest


def _reload_settings(env):
    with mock.patch.dict(os.environ, env):
        import config.settings as settings
        return importlib.reload(settings)


@pytest.fixture(autouse=True)
def restaura_settings():
    yield
    import config.settings as settings
    importlib.reload(settings)


def test_vault_db_path_via_env():
    s = _reload_settings({"VAULT_DB_PATH": "/data/vault.sqlite3"})
    assert s.DATABASES["vault"]["NAME"] == "/data/vault.sqlite3"


def test_vault_db_path_default_inalterado():
    s = _reload_settings({})
    assert s.DATABASES["vault"]["NAME"] == "vault.sqlite3"


def test_database_url_aponta_banco_principal():
    s = _reload_settings({"DATABASE_URL": "sqlite:////data/db.sqlite3"})
    assert s.DATABASES["default"]["NAME"] == "/data/db.sqlite3"


def test_document_storage_path_via_env():
    s = _reload_settings({"DOCUMENT_STORAGE_PATH": "/data/documents"})
    assert s.DOCUMENT_STORAGE_PATH == "/data/documents"
