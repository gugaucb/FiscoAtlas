import pytest
from django.test import Client as DjangoClient


@pytest.fixture
def locked_client(db):
    """Cliente sem desbloqueio (aplicação bloqueada)."""
    return DjangoClient()
