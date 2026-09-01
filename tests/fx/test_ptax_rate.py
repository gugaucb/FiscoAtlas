from decimal import Decimal
import pytest
from fx.models import PtaxRate


@pytest.mark.django_db
def test_create_ptax_rate_defaults_to_venda():
    r = PtaxRate.objects.create(
        requested_date="2026-01-05", effective_date="2026-01-05", rate=Decimal("5.43210000")
    )
    assert r.quote_type == "VENDA"
    assert r.rate == Decimal("5.4321")
    assert not r.manually_overridden
