from datetime import date
from decimal import Decimal
from unittest import mock
import pytest
from fx.models import PtaxRate
from fx.service import PtaxService

BCB_RESPONSE = {"value": [{"cotacaoData": "2026-01-05 13:00", "cotacaoVenda": 5.4321, "cotacaoCompra": 5.4211}]}


@pytest.mark.django_db
def test_caches_result_after_first_call():
    with mock.patch.object(PtaxService, "_fetch_bcb", return_value=BCB_RESPONSE) as fetch:
        first = PtaxService().get_rate(date(2026, 1, 5))
        second = PtaxService().get_rate(date(2026, 1, 5))
    assert fetch.call_count == 1
    assert first.rate == second.rate
    assert first.rate == Decimal("5.4321")


@pytest.mark.django_db
def test_saturday_falls_back_to_friday_and_records_both_dates():
    resp = {"value": [{"cotacaoData": "2026-01-02 13:00", "cotacaoVenda": 5.4000, "cotacaoCompra": 5.3900}]}
    empty = {"value": []}
    with mock.patch.object(
        PtaxService, "_fetch_bcb", side_effect=[empty, resp]
    ) as fetch:
        rate = PtaxService().get_rate(date(2026, 1, 3))  # sábado
    assert fetch.call_count == 2  # sáb (sem cotação) → sex
    assert rate.effective_date == date(2026, 1, 2)
    assert rate.requested_date == date(2026, 1, 3)


@pytest.mark.django_db
def test_cached_rate_is_reused():
    PtaxRate.objects.create(requested_date=date(2026, 3, 2), effective_date=date(2026, 3, 2), rate=Decimal("6.00000000"))
    with mock.patch.object(PtaxService, "_fetch_bcb") as fetch:
        rate = PtaxService().get_rate(date(2026, 3, 2))
    fetch.assert_not_called()
    assert rate.rate == Decimal("6.00000000")


@pytest.mark.django_db
def test_http_errors_are_skipped_in_fallback():
    import httpx
    from unittest import mock as m

    resp = {"value": [{"cotacaoData": "2026-01-02 13:00", "cotacaoVenda": 5.4000, "cotacaoCompra": 5.3900}]}
    with m.patch.object(
        PtaxService, "_fetch_bcb",
        side_effect=[httpx.HTTPStatusError("500", request=m.Mock(), response=m.Mock()), resp],
    ):
        rate = PtaxService().get_rate(date(2026, 1, 3))
    assert rate.effective_date == date(2026, 1, 2)


@pytest.mark.django_db
def test_future_date_raises_clear_error():
    import httpx
    from unittest import mock as m

    with m.patch.object(PtaxService, "_fetch_bcb", side_effect=httpx.HTTPStatusError("500", request=m.Mock(), response=m.Mock())):
        with pytest.raises(ValueError, match="PTAX"):
            PtaxService().get_rate(date(2026, 12, 31))


def test_fetch_bcb_usa_formato_mm_dd_yyyy_do_bcb():
    # BCB Olinda exige MM-DD-YYYY; DD-MM-YYYY retorna 500
    import httpx
    from unittest import mock as m

    with m.patch.object(httpx, "get") as get:
        get.return_value.json.return_value = {"value": [{"cotacaoVenda": 5.4}]}
        PtaxService()._fetch_bcb(date(2026, 1, 28))
    url = get.call_args.args[0]
    assert "'01-28-2026'" in url, f"formato errado na URL: {url}"
