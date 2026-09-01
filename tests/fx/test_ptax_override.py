from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from fx.service import PtaxService


@pytest.mark.django_db
def test_override_creates_manual_record():
    r = PtaxService().override(date(2026, 2, 10), Decimal("5.50000000"), "cotação errada no extrato")
    assert r.manually_overridden
    assert r.override_reason == "cotação errada no extrato"


@pytest.mark.django_db
def test_override_requires_reason():
    with pytest.raises(ValueError):
        PtaxService().override(date(2026, 2, 10), Decimal("5.5"), "")


@pytest.mark.django_db
def test_get_rate_prefers_override():
    PtaxService().override(date(2026, 2, 10), Decimal("5.50000000"), "manual")
    with mock.patch.object(PtaxService, "_fetch_bcb"):
        r = PtaxService().get_rate(date(2026, 2, 10))
    assert r.rate == Decimal("5.50000000")
