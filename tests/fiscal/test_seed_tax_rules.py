import pytest
from fiscal.models import TaxRule


@pytest.mark.django_db
def test_seed_creates_years_2024_to_2026():
    from django.core.management import call_command
    call_command("seed_tax_rules")
    years = set(TaxRule.objects.values_list("tax_year", flat=True))
    assert years == {2024, 2025, 2026}
    # V1 histórica fica desconfirmada; V2 (Lei 14.754/2023) nasce confirmada
    assert all(not r.confirmed for r in TaxRule.objects.filter(rule_version="V1"))
    assert all(r.confirmed for r in TaxRule.objects.filter(rule_version="V2"))


@pytest.mark.django_db
def test_seed_is_idempotent():
    from django.core.management import call_command
    call_command("seed_tax_rules")
    call_command("seed_tax_rules")
    assert TaxRule.objects.count() == 6


@pytest.mark.django_db
def test_seed_creates_v2_flat_15_percent():
    from django.core.management import call_command
    call_command("seed_tax_rules")
    v2 = TaxRule.objects.filter(tax_year=2026, rule_version="V2").first()
    assert v2 is not None
    assert v2.brackets == [{"limit_brl": None, "rate": "0.15"}]
    assert v2.confirmed
    for year in (2024, 2025, 2026):
        assert TaxRule.objects.filter(tax_year=year, rule_version="V2").exists()
