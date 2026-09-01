from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from ledger.models import BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")


@pytest.mark.django_db
def test_juros_requires_interest_bearing_account():
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="1", is_interest_bearing=False)
    with pytest.raises(ValueError, match="não remunerada"):
        with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
            EventService().record(dict(
                event_type="JUROS", account=acct, trade_date=date(2026, 4, 1),
                amount_usd=Decimal(10),
            ))


@pytest.mark.django_db
def test_juros_allowed_on_interest_bearing_account():
    acct = BrokerAccount.objects.create(broker_name="Avenue", account_number="2", is_interest_bearing=True)
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        ev = EventService().record(dict(
            event_type="JUROS", account=acct, trade_date=date(2026, 4, 1),
            amount_usd=Decimal(10),
        ))
    assert ev.amount_usd == Decimal(10)
