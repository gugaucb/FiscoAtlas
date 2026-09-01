from datetime import date, timedelta
from decimal import Decimal

import httpx

from fx.models import PtaxRate

BCB_URL = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='{dd-mm-yyyy}'"
    "&$format=json"
)


class PtaxService:
    def get_rate(self, requested: date, quote_type: str = "VENDA") -> PtaxRate:
        overridden = PtaxRate.objects.filter(
            requested_date=requested, quote_type=quote_type, manually_overridden=True
        ).order_by("-fetched_at").first()
        if overridden:
            return overridden
        cached = PtaxRate.objects.filter(
            requested_date=requested, quote_type=quote_type, manually_overridden=False
        ).first()
        if cached:
            return cached
        effective = requested
        max_lookback = 10  # dias úteis são suficientes; mais que isso é data sem cotação (ex.: futura)
        for _ in range(max_lookback):
            try:
                data = self._fetch_bcb(effective)
            except httpx.HTTPError:  # status 4xx/5xx, conexão, timeout
                effective -= timedelta(days=1)
                continue
            if data["value"]:
                return PtaxRate.objects.create(
                    requested_date=requested,
                    effective_date=effective,
                    quote_type=quote_type,
                    rate=Decimal(str(data["value"][-1][f"cotacao{quote_type.capitalize()}"])),
                )
            effective -= timedelta(days=1)
        raise ValueError(
            f"PTAX indisponível para {requested.strftime('%d/%m/%Y')} nos {max_lookback} dias anteriores. "
            "Se a data é futura (sem cotação publicada), cadastre uma taxa manual (override)."
        )

    def override(self, requested: date, new_rate: Decimal, reason: str, quote_type: str = "VENDA") -> PtaxRate:
        if not reason:
            raise ValueError("override_reason é obrigatório")
        return PtaxRate.objects.create(
            requested_date=requested,
            effective_date=requested,
            quote_type=quote_type,
            rate=new_rate,
            source="MANUAL",
            manually_overridden=True,
            override_reason=reason,
        )

    def _fetch_bcb(self, day: date) -> dict:
        resp = httpx.get(BCB_URL.replace("{dd-mm-yyyy}", day.strftime("%m-%d-%Y")), timeout=30)  # BCB exige MM-DD-YYYY
        resp.raise_for_status()
        return resp.json()
