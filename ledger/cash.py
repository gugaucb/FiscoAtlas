from decimal import Decimal

from ledger.models import FinancialEvent

INFLOWS = {"APORTE", "SELL", "DIVIDEND", "JUROS"}


class CashLedgerService:
    def _cash_delta(self, ev) -> Decimal:
        """Efeito do evento no caixa. Custódia de ATIVOS não movimenta caixa
        (o amount_usd dela é custo fiscal, não dinheiro). Na transferência de
        caixa, a ponta OUT é registrada com amount positivo e deve SUBTRAIR.
        Demais saídas (BUY/WITHDRAWAL/FEE/TAX) já são negativas."""
        if ev.asset_id and ev.event_type in ("BROKER_TRANSFER_OUT", "BROKER_TRANSFER_IN"):
            return Decimal(0)
        if ev.event_type == "BROKER_TRANSFER_OUT":
            return -ev.amount_usd
        return ev.amount_usd

    def balance(self, account, until=None) -> Decimal:
        total = Decimal(0)
        events = FinancialEvent.objects.filter(account=account, active=True)
        if until:
            events = events.filter(trade_date__lte=until)
        for ev in events.order_by("trade_date", "id"):
            total += self._cash_delta(ev)
        return total

    def history(self, account) -> list[dict]:
        out = []
        running = Decimal(0)
        for ev in FinancialEvent.objects.filter(
            account=account, active=True
        ).order_by("trade_date", "id"):
            running += self._cash_delta(ev)
            out.append({"event": ev, "balance": running})
        return out
