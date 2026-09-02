from datetime import date
from decimal import Decimal

from django.db.models import Sum

from fiscal.engine import TaxEngine, fx_imposto_exterior
from fiscal.models import AnnualAssessment, Profile
from fx.service import PtaxService
from ledger.cash import INFLOWS, CashLedgerService
from ledger.models import Asset, BrokerAccount, FinancialEvent
from ledger.position import PositionService

# Códigos da ficha Bens e Direitos (DIRPF) — a confirmar com contador
GRUPO_CODIGO = {"STOCK": "03/01", "ETF": "03/02", "REIT": "03/03", "FUND": "03/99", "BOND": "04/99", "OTHER": "99/99"}
# Tabela de países da RFB: 249 = Estados Unidos
COUNTRY_RFB = {"US": ("249", "Estados Unidos")}


class ReportService:
    def __init__(self, year: int):
        self.year = year

    def build(self) -> dict:
        yearend = date(self.year, 12, 31)
        ptax = PtaxService().get_rate(yearend)

        assets = []
        cash = []
        exempt_accounts = []
        prev_yearend = date(self.year - 1, 12, 31)
        for account in BrokerAccount.objects.filter(active=True):
            balance_usd = CashLedgerService().balance(account, until=yearend)
            cash.append({
                "account": account,
                "balance_usd": balance_usd,
                "balance_brl": (balance_usd * ptax.rate).quantize(Decimal("0.01")),
            })
            if not account.is_interest_bearing:
                # Variação cambial de caixa não remunerado é isenta
                # (IN RFB 2180/2024, art. 3º): saldo a PTAX 31/12 − custo BRL
                # das entradas do ano; desvalorização → 0.
                inflows_brl = FinancialEvent.objects.filter(
                    account=account, active=True,
                    event_type__in=INFLOWS, trade_date__year=self.year,
                ).aggregate(t=Sum("amount_brl"))["t"] or Decimal(0)
                variation = (balance_usd * ptax.rate).quantize(Decimal("0.01")) - inflows_brl
                exempt_accounts.append({
                    "account": account,
                    "exempt_brl": max(variation, Decimal("0.00")),
                })
            from django.db.models import Q
            from ledger.models import OpeningPosition
            assets_qs = Asset.objects.filter(
                Q(events__account=account, events__active=True) | Q(opening_positions__isnull=False)
            ).distinct()
            for asset in assets_qs:
                pos = PositionService().position(account, asset, until=yearend)
                if pos["quantity"]:
                    prev = PositionService().position(account, asset, until=prev_yearend)
                    cost_usd_total = (pos["avg_cost_usd"] * pos["quantity"]).quantize(Decimal("0.01"))
                    ptax_media = (
                        pos["cost_brl_total"] / cost_usd_total
                        if cost_usd_total else Decimal(0)
                    ).quantize(Decimal("0.00000001"))
                    div_events = FinancialEvent.objects.filter(
                        account=account, asset=asset, active=True,
                        event_type__in=("DIVIDEND", "JUROS"), trade_date__year=self.year,
                    ).prefetch_related("foreign_tax_payments")
                    dividends_brl = Decimal(0)
                    withholding_brl = Decimal(0)
                    ptax_service = PtaxService()
                    for ev in div_events:
                        fx = ev.fx_rate or Decimal(0)
                        dividends_brl += (ev.amount_usd + ev.tax_usd) * fx
                        # imposto pago no exterior: PTAX COMPRA na data do pagamento
                        pagamento = ev.foreign_tax_payments.first()
                        fx_tax = fx_imposto_exterior(ev, pagamento, ptax_service)
                        withholding_brl += ev.tax_usd * fx_tax
                    gains_brl = Decimal(0)
                    losses_brl = Decimal(0)
                    for r in PositionService().realized(account, asset, until=yearend):
                        if r["event"].trade_date.year == self.year:
                            if r["gain_brl"] > 0:
                                gains_brl += r["gain_brl"]
                            else:
                                losses_brl += -r["gain_brl"]
                    assets.append({
                        "asset": asset, **pos,
                        "prev_cost_brl": prev["cost_brl_total"],
                        "cost_usd_total": cost_usd_total,
                        "ptax_media": ptax_media,
                        "dividends_brl": dividends_brl.quantize(Decimal("0.01")),
                        "withholding_brl": withholding_brl.quantize(Decimal("0.01")),
                        "gains_brl": gains_brl.quantize(Decimal("0.01")),
                        "losses_brl": losses_brl.quantize(Decimal("0.01")),
                    })

        assets.sort(key=lambda a: a["asset"].ticker)
        income = TaxEngine(self.year).compute()
        # Evidência do crédito de imposto pago no exterior por rendimento:
        # limite de 15% sobre o bruto (Lei 14.754/2023, art. 5º); crédito
        # excedente é descartado (sem carryforward de crédito).
        rate = Decimal(income["rule"].brackets[-1]["rate"])
        income["credit_detail"] = [
            {
                "description": str(d["event"]),
                "gross_brl": d["gross_brl"],
                "limit_brl": (d["gross_brl"] * rate).quantize(Decimal("0.01")),
                "withholding_brl": d["withholding_brl"],
                "credit_used_brl": d["credit_used"],
                "credit_unused_brl": (d["withholding_brl"] - d["credit_used"]).quantize(Decimal("0.01")),
            }
            for d in income["detail"] if d["withholding_brl"] > 0
        ]

        profile = Profile.objects.first()
        snapshot = AnnualAssessment.objects.filter(year=self.year).first()
        prev_snapshot = AnnualAssessment.objects.filter(year=self.year - 1).first()
        return {
            "closing": {
                "is_closed": snapshot is not None,
                "closed_at": snapshot.computed_at if snapshot else None,
                "prev_closed": prev_snapshot is not None,
            },
            "year": self.year,
            "exercise": self.year + 1,
            "beneficiary": {"name": profile.name, "cpf": profile.cpf} if profile else {"name": "", "cpf": ""},
            "identification": [
                {"broker_name": a.broker_name, "account_number": a.account_number,
                 "country_code": a.country_code}
                for a in BrokerAccount.objects.filter(active=True)
            ],
            "assets": [
                {"ticker": a["asset"].ticker, "description": a["asset"].description,
                 "asset_type": a["asset"].asset_type, "quantity": a["quantity"],
                 "avg_cost_usd": a["avg_cost_usd"], "cost_brl_total": a["cost_brl_total"],
                 "prev_cost_brl": a["prev_cost_brl"], "cost_usd_total": a["cost_usd_total"],
                 "ptax_media": a["ptax_media"], "dividends_brl": a["dividends_brl"],
                 "withholding_brl": a["withholding_brl"], "gains_brl": a["gains_brl"],
                 "losses_brl": a["losses_brl"],
                 "grupo_codigo": GRUPO_CODIGO.get(a["asset"].asset_type, "03/99"),
                 "country_code_rfb": COUNTRY_RFB.get(a["asset"].country_code, ("", ""))[0],
                 "country_name": COUNTRY_RFB.get(a["asset"].country_code, ("", a["asset"].country_code))[1],
                 "cost_usd_text": f"US$ {a['cost_usd_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                 "discriminacao": (
                     f"{a['quantity']} de {a['asset'].description} ({a['asset'].ticker}), "
                     f"custo total de aquisição US$ {a['cost_usd_total']:,.2f}, "
                     f"custo fiscal R$ {a['cost_brl_total']:,.2f}"
                 ).replace(",", "X").replace(".", ",").replace("X", "."),
             }
                for a in assets
            ],
            "cash": cash,
            "exempt": {
                "accounts": exempt_accounts,
                "total_brl": sum((e["exempt_brl"] for e in exempt_accounts), Decimal("0")),
                "legal_basis": "IN RFB 2180/2024, art. 3º",
            },
            "income": income,
            "ptax_yearend": {"rate": ptax.rate, "effective_date": ptax.effective_date},
        }
