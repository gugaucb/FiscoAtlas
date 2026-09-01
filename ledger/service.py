from decimal import Decimal

from fx.service import PtaxService
from ledger.models import FinancialEvent
from ledger.position import PositionService

TOL = Decimal("0.01")


class EventService:
    def __init__(self, ptax: PtaxService | None = None):
        self.ptax = ptax or PtaxService()

    def _ptax_rate(self, trade_date) -> Decimal:
        return self.ptax.get_rate(trade_date).rate

    def record(self, data: dict) -> FinancialEvent:
        etype = data["event_type"]
        qty, price = data.get("quantity"), data.get("price_usd")
        fee = data.get("fee_usd") or Decimal(0)
        tax = data.get("tax_usd") or Decimal(0)

        if etype == "JUROS" and not data["account"].is_interest_bearing:
            raise ValueError("JUROS só é válido em conta remunerada; conta não remunerada")
        if etype in ("BUY", "SELL") and (not qty or not price or qty <= 0 or price <= 0):
            raise ValueError("quantity e price_usd devem ser positivos para BUY/SELL")
        if etype == "BUY":
            expected = -(qty * price + fee)
        elif etype == "SELL":
            expected = qty * price - fee
        elif etype == "DIVIDEND":
            expected = data.get("per_share_usd", Decimal(0)) * qty - tax
        else:  # APORTE, WITHDRAWAL, JUROS, FEE, TAX_WITHHELD
            expected = data["amount_usd"]
            if etype in ("WITHDRAWAL", "FEE", "TAX_WITHHELD"):
                # saídas de caixa: converte para negativo independente do sinal informado
                expected = -abs(expected)

        informed = data.get("amount_usd")
        if etype in ("BUY", "SELL", "DIVIDEND") and informed is not None and abs(informed - expected) > TOL:
            raise ValueError(f"amount_usd diverge do calculado: esperado {expected}")

        if etype == "SELL":
            pos = PositionService().position(data["account"], data["asset"])
            if pos["quantity"] < qty:
                raise ValueError(f"posição insuficiente: {pos['quantity']} < {qty}")

        manual_rate = data.pop("ptax_manual", None)
        manual_reason = data.pop("ptax_reason", None)
        if manual_rate:
            rate = self.ptax.override(
                data["trade_date"], Decimal(str(manual_rate)), manual_reason or ""
            ).rate
        else:
            rate = self._ptax_rate(data["trade_date"])
        if data.get("corrects"):
            data["corrects"].active = False
            data["corrects"].save()
        fields = {k: v for k, v in data.items() if k not in ("amount_usd", "corrects", "per_share_usd")}
        fields["fee_usd"] = fields.get("fee_usd") or Decimal(0)
        fields["tax_usd"] = fields.get("tax_usd") or Decimal(0)
        return FinancialEvent.objects.create(
            **fields,
            corrects=data.get("corrects"),
            amount_usd=expected,
            fx_rate=rate,
            amount_brl=(expected * rate).quantize(Decimal("0.00000001")),
        )
