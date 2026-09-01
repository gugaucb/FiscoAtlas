from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from fiscal.engine import TaxEngine
from fiscal.models import AnnualAssessment, TaxRule
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")


@pytest.mark.django_db
def test_snapshot_upsert():
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2",
        brackets=[{"limit_brl": None, "rate": "0.15"}],
        confirmed=True, effective_from="2026-01-01", effective_until="2026-12-31",
    )
    snap = TaxEngine.save_snapshot(2026)
    assert snap.year == 2026
    assert snap.income_brl == Decimal("0.00")
    again = TaxEngine.save_snapshot(2026)
    assert again.pk == snap.pk
    assert AnnualAssessment.objects.count() == 1
