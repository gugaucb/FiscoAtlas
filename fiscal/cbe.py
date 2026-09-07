"""CBE — Declaração de Capitais Brasileiros no Exterior (RF-CBE-001..007).

Resolução BCB nº 278/2022: capitais ≥ US$ 1.000.000,00 na data-base 31/12
exigem CBE anual; ≥ US$ 100.000.000,00, declaração trimestral. Abaixo do
limite o status é indeterminado (a plataforma não enxerga bens fora dela),
salvo declaração formal de completude patrimonial do contribuinte.
"""
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum

from fiscal.models import Profile
from ledger.models import FinancialEvent
from ledger.position import PositionService

LIMITE_ANUAL_USD = Decimal(1_000_000)
LIMITE_TRIMESTRAL_USD = Decimal(100_000_000)


class CbeService:
    def __init__(self, year: int):
        self.year = year

    def _data_base(self) -> date:
        return date(self.year, 12, 31)

    def evaluate(self) -> dict:
        ate = self._data_base()
        total_usd = self._caixa_usd(ate) + self._patrimonio_usd(ate)
        total_usd = total_usd.quantize(Decimal("0.01"))

        if total_usd >= LIMITE_TRIMESTRAL_USD:
            status, quarterly = "CBE_REQUIRED", True
        elif total_usd >= LIMITE_ANUAL_USD:
            status, quarterly = "CBE_REQUIRED", False
        else:
            profile = Profile.objects.first()
            completo = bool(profile and profile.external_assets_declared_complete)
            status = "CBE_NOT_REQUIRED" if completo else "CBE_UNDETERMINED"
            quarterly = False
        return {"status": status, "quarterly": quarterly, "total_usd": total_usd}

    def _caixa_usd(self, ate: date) -> Decimal:
        """Caixa = soma dos eventos sem ativo (APORTE/retiradas/juros/taxas)."""
        return (
            FinancialEvent.objects.filter(
                active=True, asset__isnull=True, trade_date__lte=ate,
                trade_date__year__lte=self.year,
            ).aggregate(s=Sum("amount_usd"))["s"]
            or Decimal(0)
        )

    def _patrimonio_usd(self, ate: date) -> Decimal:
        """Custódia: posição em 31/12 × custo médio USD (proxy conservador do
        valor patrimonial — a plataforma não registra preço de mercado)."""
        total = Decimal(0)
        contas_ids = set(
            FinancialEvent.objects.filter(
                active=True, asset__isnull=False, trade_date__lte=ate,
            ).values_list("account_id", flat=True)
        )
        if not contas_ids:
            return total
        ativos_ids = set(
            FinancialEvent.objects.filter(
                active=True, asset__isnull=False, trade_date__lte=ate,
            ).values_list("asset_id", flat=True)
        )
        from ledger.models import Asset, BrokerAccount
        for conta in BrokerAccount.objects.filter(id__in=contas_ids):
            for asset in Asset.objects.filter(id__in=ativos_ids):
                pos = PositionService().position(conta, asset, until=ate)
                if pos["quantity"]:
                    total += pos["quantity"] * pos["avg_cost_usd"]
        return total
