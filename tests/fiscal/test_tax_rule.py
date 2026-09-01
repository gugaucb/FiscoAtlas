import pytest
from fiscal.models import TaxRule

BRACKETS_2026 = [
    {"limit_brl": "6000.00", "rate": "0.00"},
    {"limit_brl": "50000.00", "rate": "0.15"},
    {"limit_brl": None, "rate": "0.225"},
]


@pytest.mark.django_db
def test_for_year_returns_confirmed_rule():
    TaxRule.objects.create(
        tax_year=2026, rule_version="V1", brackets=BRACKETS_2026,
        confirmed=True, effective_from="2026-01-01", effective_until="2026-12-31",
    )
    rule = TaxRule.objects.for_year(2026)
    assert rule.rule_version == "V1"
    assert rule.brackets[0]["limit_brl"] == "6000.00"


@pytest.mark.django_db
def test_for_year_ignores_unconfirmed():
    TaxRule.objects.create(
        tax_year=2026, rule_version="V1", brackets=BRACKETS_2026, confirmed=False,
        effective_from="2026-01-01", effective_until="2026-12-31",
    )
    with pytest.raises(ValueError, match="2026"):
        TaxRule.objects.for_year(2026)


@pytest.mark.django_db
def test_for_year_picks_latest_version():
    TaxRule.objects.create(
        tax_year=2026, rule_version="V1", brackets=BRACKETS_2026, confirmed=True,
        effective_from="2026-01-01", effective_until="2026-12-31",
    )
    TaxRule.objects.create(
        tax_year=2026, rule_version="V2", brackets=BRACKETS_2026, confirmed=True,
        effective_from="2026-01-01", effective_until="2026-12-31",
    )
    assert TaxRule.objects.for_year(2026).rule_version == "V2"
