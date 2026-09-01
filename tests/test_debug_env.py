"""DEBUG controlado por env (Docker roda com DEBUG=False)."""
import importlib
import os
from unittest import mock

import pytest


def _reload_debug(env):
    with mock.patch.dict(os.environ, env):
        import config.settings as settings
        importlib.reload(settings)
        return settings


@pytest.fixture(autouse=True)
def restaura_settings():
    yield
    import config.settings as settings
    importlib.reload(settings)


def test_debug_default_true_preserva_local():
    s = _reload_debug({})
    assert s.DEBUG is True


def test_debug_false_via_env():
    s = _reload_debug({"DJANGO_DEBUG": "False"})
    assert s.DEBUG is False
