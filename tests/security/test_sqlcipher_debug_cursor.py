"""Bug do cursor de DEBUG com driver sqlcipher3.

Com DEBUG=True (runsecure padrão), django.db.backends.utils.debug_sql chama
operations.last_executed_query, que faz mogrify dos parâmetros BRUTOS em um
cursor cru do driver. O sqlcipher3 não registra o adapter de Decimal (ver
ticket 08) e quebra com InterfaceError em qualquer lookup com Decimal —
ex.: LossLedgerService.open_records (remaining_brl__gt).
"""
from decimal import Decimal

import pytest

pytestmark = pytest.mark.django_db


def test_debug_cursor_nao_quebra_com_param_decimal(settings):
    from fiscal.models import LossRecord
    from ledger.models import FinancialEvent

    LossRecord.objects.create(
        origin_year=2025, description="teste", amount_brl=Decimal("100.00"),
        remaining_brl=Decimal("100.00"),
    )
    settings.DEBUG = True
    from django.db import connection

    connection.force_debug_cursor = True
    try:
        # parâmetro Decimal vindo do campo DecimalField (gt lookup)
        list(LossRecord.objects.filter(remaining_brl__gt=Decimal("0")))
        list(FinancialEvent.objects.filter(amount_usd__gte=Decimal("1")))
    finally:
        connection.force_debug_cursor = False
        connection.queries_log.clear()
