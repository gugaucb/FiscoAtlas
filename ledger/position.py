from datetime import date as date_cls
from decimal import Decimal

from ledger.models import FinancialEvent, OpeningPosition

OPENING_DATE = date_cls(2025, 12, 31)


class PositionService:
    @staticmethod
    def _opening(asset, until=None) -> dict:
        """Custo fiscal de abertura (31/12/2025) já convertido em BRL."""
        if until and until < OPENING_DATE:
            return {"quantity": Decimal(0), "cost_brl": Decimal(0)}
        op = OpeningPosition.objects.filter(asset=asset).first()
        if not op:
            return {"quantity": Decimal(0), "cost_brl": Decimal(0)}
        return {"quantity": op.quantity, "cost_brl": op.total_cost_brl}

    def position(self, account, asset, until=None, exclude_event_id=None) -> dict:
        opening = self._opening(asset, until)
        qty = opening["quantity"]
        cost_usd = Decimal(0)
        cost_brl = opening["cost_brl"]
        events = FinancialEvent.objects.filter(
            account=account, asset=asset, active=True
        )
        if exclude_event_id:
            # custódia ANTERIOR a um evento específico (ex.: a própria venda
            # no check de venda a descoberto — liquidar 100% é legítimo)
            events = events.exclude(pk=exclude_event_id)
        if until:
            events = events.filter(trade_date__lte=until)
        events = events.order_by("trade_date", "id")
        for ev in events:
            if ev.event_type == "BUY":
                cost_usd += ev.quantity * ev.price_usd + ev.fee_usd
                cost_brl += abs(ev.amount_brl)
                qty += ev.quantity
            elif ev.event_type in ("STOCK_SPLIT", "REVERSE_SPLIT"):
                # RF-CA-002: quantidade × razão; custo total BRL inalterado
                razao = ev.split_ratio_to / ev.split_ratio_from
                qty = qty * razao
                # custos totais (USD e BRL) preservados; unitário se ajusta
            elif ev.event_type == "BROKER_TRANSFER_IN":
                # RF-CST-003: entrada transporta custo integral (não é compra)
                cost_usd += ev.amount_usd
                cost_brl += abs(ev.amount_brl or 0)
                qty += ev.quantity
            elif ev.event_type == "BROKER_TRANSFER_OUT":
                # saída proporcional (não é alienação)
                avg = cost_usd / qty if qty else Decimal(0)
                avg_brl = cost_brl / qty if qty else Decimal(0)
                sold_qty = ev.quantity
                cost_usd -= avg * sold_qty
                cost_brl -= avg_brl * sold_qty
                qty -= sold_qty
            elif ev.event_type in ("SELL", "CASH_IN_LIEU"):
                avg = cost_usd / qty if qty else Decimal(0)
                avg_brl = cost_brl / qty if qty else Decimal(0)
                sold_qty = ev.quantity
                cost_usd -= avg * sold_qty
                cost_brl -= avg_brl * sold_qty
                qty -= sold_qty
        avg = cost_usd / qty if qty else Decimal(0)
        return {"quantity": qty, "avg_cost_usd": avg, "cost_brl_total": cost_brl}

    def realized(self, account, asset, until=None) -> list[dict]:
        """Resultado em BRL por venda: alienação BRL (PTAX da venda) − custo
        baixado BRL (PTAX da compra). A variação cambial integra o rendimento
        (Lei 14.754/2023, art. 3º, II). Cash-in-lieu apura como alienação."""
        qty = Decimal(0)
        cost_usd = Decimal(0)
        cost_brl = Decimal(0)
        opening = self._opening(asset, until)
        qty = opening["quantity"]
        cost_brl = opening["cost_brl"]
        out = []
        events = FinancialEvent.objects.filter(
            account=account, asset=asset, active=True,
            event_type__in=("BUY", "SELL", "STOCK_SPLIT", "REVERSE_SPLIT", "CASH_IN_LIEU",
                            "BROKER_TRANSFER_IN", "BROKER_TRANSFER_OUT"),
        )
        if until:
            events = events.filter(trade_date__lte=until)
        events = events.order_by("trade_date", "id")
        for ev in events:
            if ev.event_type == "BUY":
                cost_usd += ev.quantity * ev.price_usd + ev.fee_usd
                cost_brl += abs(ev.amount_brl or 0)
                qty += ev.quantity
            elif ev.event_type in ("STOCK_SPLIT", "REVERSE_SPLIT"):
                razao = ev.split_ratio_to / ev.split_ratio_from
                qty = qty * razao
                # custos totais (USD e BRL) preservados; unitário se ajusta
            elif ev.event_type == "BROKER_TRANSFER_IN":
                cost_usd += ev.amount_usd
                cost_brl += abs(ev.amount_brl or 0)
                qty += ev.quantity
            elif ev.event_type == "BROKER_TRANSFER_OUT":
                # sai do custo médio proporcional; sem apuração (RF-CST-003)
                avg_usd = cost_usd / qty if qty else Decimal(0)
                avg_brl = cost_brl / qty if qty else Decimal(0)
                cost_usd -= avg_usd * ev.quantity
                cost_brl -= avg_brl * ev.quantity
                qty -= ev.quantity
            else:
                avg_usd = cost_usd / qty if qty else Decimal(0)
                avg_brl = cost_brl / qty if qty else Decimal(0)
                sale_brl = (ev.amount_usd * (ev.fx_rate or Decimal(0))).quantize(Decimal("0.01"))
                cost_sold_brl = (avg_brl * ev.quantity).quantize(Decimal("0.01"))
                gain_brl = (sale_brl - cost_sold_brl).quantize(Decimal("0.01"))
                gain_usd = ev.amount_usd - avg_usd * ev.quantity
                out.append({
                    "event": ev, "avg_cost_usd": avg_usd,
                    "gain_usd": gain_usd, "gain_brl": gain_brl,
                    "sale_brl": sale_brl, "cost_sold_brl": cost_sold_brl,
                })
                cost_usd -= avg_usd * ev.quantity
                cost_brl -= cost_sold_brl
                qty -= ev.quantity
        return out
