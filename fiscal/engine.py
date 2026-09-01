from decimal import Decimal

from fiscal.models import AnnualAssessment, TaxRule
from ledger.models import FinancialEvent
from ledger.position import PositionService

ZERO = Decimal("0.00")


class TaxEngine:
    def __init__(self, year: int):
        self.year = year

    @classmethod
    def save_snapshot(cls, year: int) -> AnnualAssessment:
        result = cls(year).compute()
        rule = result["rule"]
        defaults = {
            "rule_version": rule.rule_version,
            "income_brl": result["income_brl"],
            "loss_brl": result["loss_brl"],
            "taxable_brl": result["taxable_brl"],
            "tax_brl": result["tax_brl"],
            "withholding_credit_brl": result["withholding_credit_brl"],
            "tax_due_brl": result["tax_due_brl"],
            "loss_carryforward_brl": result["loss_carryforward_brl"],
            "detail": [
                {
                    "event_id": d["event"].id, "kind": d["kind"],
                    "description": str(d["event"]),
                    "gross_brl": str(d["gross_brl"]),
                    "withholding_brl": str(d["withholding_brl"]),
                    "credit_used": str(d["credit_used"]),
                }
                for d in result["detail"]
            ],
        }
        assessment, _ = AnnualAssessment.objects.update_or_create(year=year, defaults=defaults)
        return assessment

    def compute(self) -> dict:
        rule = TaxRule.objects.for_year(self.year)
        rate = Decimal(rule.brackets[-1]["rate"])
        events = list(
            FinancialEvent.objects.filter(
                active=True, trade_date__year=self.year,
                event_type__in=("DIVIDEND", "JUROS", "SELL"),
            ).select_related("asset").order_by("trade_date", "id")
        )

        realized_idx = {}
        account_ids = {ev.account_id for ev in events}
        asset_ids = {ev.asset_id for ev in events if ev.asset_id}
        for account_id in account_ids:
            for asset_id in asset_ids:
                for r in PositionService().realized(account_id, asset_id):
                    if r["event"].trade_date.year == self.year:
                        realized_idx[r["event"].id] = r

        detail = []
        income = ZERO
        loss = ZERO
        credit = ZERO
        for ev in events:
            fx = ev.fx_rate or ZERO
            if ev.event_type == "SELL":
                r = realized_idx.get(ev.id)
                if r is None:
                    continue
                gain_brl = r["gain_brl"]
                gross_brl = gain_brl if gain_brl > 0 else ZERO
                if gain_brl < 0:
                    loss += -gain_brl
                income += gross_brl
                detail.append({
                    "event": ev, "kind": "gain/loss", "gross_brl": gross_brl,
                    "sale_brl": r["sale_brl"], "cost_sold_brl": r["cost_sold_brl"],
                    "withholding_brl": ZERO, "credit_used": ZERO,
                })
            else:  # DIVIDEND, JUROS
                gross_usd = ev.amount_usd + ev.tax_usd
                gross_brl = (gross_usd * fx).quantize(Decimal("0.01"))
                income += gross_brl
                wh_brl = (ev.tax_usd * fx).quantize(Decimal("0.01"))
                used = min(wh_brl, (gross_brl * rate).quantize(Decimal("0.01")))
                credit += used
                detail.append({
                    "event": ev, "kind": ev.event_type.lower(), "gross_brl": gross_brl,
                    "withholding_brl": wh_brl, "credit_used": used,
                })

        # Prejuízo herdado de anos anteriores (P&R IRPF: prejuízos são
        # compensáveis nos anos seguintes). Fonte: AnnualAssessment do ano
        # anterior (saldo não compensado). Perdas do ano têm prioridade.
        prev = AnnualAssessment.objects.filter(year=self.year - 1).first()
        loss_inherited = prev.loss_carryforward_brl if prev else ZERO
        total_loss_available = loss + loss_inherited

        taxable = max(income - total_loss_available, ZERO)
        excess_loss = max(total_loss_available - income, ZERO)
        tax = (taxable * rate).quantize(Decimal("0.01"))
        if loss_inherited > 0:
            detail.insert(0, {
                "event": None, "kind": "loss_carryforward",
                "gross_brl": -loss_inherited,
                "description": f"Prejuízo a compensar de {self.year - 1}",
                "withholding_brl": ZERO, "credit_used": ZERO,
            })
        return {
            "income_brl": income,
            "loss_brl": loss,
            "loss_inherited_brl": loss_inherited,
            "taxable_brl": taxable,
            "tax_brl": tax,
            "withholding_credit_brl": credit,
            "tax_due_brl": max(tax - credit, ZERO),
            "loss_carryforward_brl": excess_loss,
            "detail": detail,
            "rule": rule,
        }
