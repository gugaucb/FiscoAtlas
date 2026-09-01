from decimal import Decimal

from ledger.models import FinancialEvent

INFLOWS = {"APORTE", "SELL", "DIVIDEND", "JUROS"}


class CashLedgerService:
    def balance(self, account, until=None) -> Decimal:
        total = Decimal(0)
        events = FinancialEvent.objects.filter(account=account, active=True)
        if until:
            events = events.filter(trade_date__lte=until)
        for ev in events.order_by("trade_date", "id"):
            total += ev.amount_usd  # saídas (BUY/WITHDRAWAL/FEE/TAX) já são negativas
        return total

    def history(self, account) -> list[dict]:
        out = []
        running = Decimal(0)
        for ev in FinancialEvent.objects.filter(
            account=account, active=True
        ).order_by("trade_date", "id"):
            running += ev.amount_usd
            out.append({"event": ev, "balance": running})
        return out
