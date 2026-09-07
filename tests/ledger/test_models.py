import pytest
from django.db import IntegrityError
from ledger.models import Asset, BrokerAccount


@pytest.mark.django_db
def test_asset_unique_ticker():
    Asset.objects.create(ticker="AAPL", description="Apple Inc.", asset_type="FOREIGN_EQUITY")
    with pytest.raises(IntegrityError):
        Asset.objects.create(ticker="AAPL", description="dup", asset_type="FOREIGN_EQUITY")


@pytest.mark.django_db
def test_avenue_account_defaults():
    acct = BrokerAccount.objects.create(
        broker_name="Avenue Securities LLC", account_number="12345",
        country_code="US", currency="USD", account_type="CASH",
        is_interest_bearing=False,
    )
    assert acct.active is True
    assert acct.is_interest_bearing is False
