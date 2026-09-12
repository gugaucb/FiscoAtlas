from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum

from fiscal.cbe import CbeService
from fiscal.darf import DarfGuideService
from fiscal.date_rules import income_fiscal_year_q
from fiscal.engine import TaxEngine, fx_imposto_exterior
from fiscal.high_income import HighIncomeService
from fiscal.models import AnnualAssessment, Profile
from fx.service import PtaxService
from ledger.cash import INFLOWS, CashLedgerService
from ledger.models import Asset, BrokerAccount, FinancialEvent
from ledger.ownership import OwnershipService
from ledger.position import PositionService

# Códigos da ficha Bens e Direitos (DIRPF) — a confirmar com contador
GRUPO_CODIGO = {
    "FOREIGN_EQUITY": "03/01", "FOREIGN_ETF": "03/02", "REIT": "03/03",
    "FOREIGN_FUND": "03/99", "US_TREASURY": "04/99", "FOREIGN_BOND": "04/99",
    "OTHER": "99/99",
}
# Tabela de países da RFB: 249 = Estados Unidos
COUNTRY_RFB = {"US": ("249", "Estados Unidos")}


class ReportService:
    def __init__(self, year: int):
        self.year = year

    def _dirpf_schema(self) -> dict:
        """RF-ARQ-002/003: códigos por exercício com trava de homologação.
        Auditoria-fiscal 11: sem schema configurado o relatório NÃO se
        autodenomina homologado — defaults estáticos viram PRELIMINAR
        (com aviso). HOMOLOGADO só com schema explicitamente homologado.
        A apuração matemática continua funcionando sem schema."""
        from fiscal.models import DirpfSchema
        # exercício = ano-calendário + 1: o schema que vale para o ano-
        # calendário 2026 é o do exercício 2027 (mesma convenção do
        # FilingRule do guia DARF); consultar o próprio ano usaria o schema
        # de um exercício errado.
        schema = DirpfSchema.objects.filter(filing_year=self.year + 1).first()
        if schema is None:
            return {
                "groups": GRUPO_CODIGO, "countries": COUNTRY_RFB,
                "schema_version": "default", "status": "PRELIMINAR",
                "aviso": (
                    "Nenhum schema de códigos DIRPF cadastrado para o "
                    f"exercício {self.year + 1}: o relatório usa defaults "
                    "estáticos e é PRELIMINAR. Cadastre e homologue o schema "
                    "em DirpfSchema para o status HOMOLOGADO."
                ),
            }
        return {
            "groups": {**GRUPO_CODIGO, **(schema.groups or {})},
            "countries": {**COUNTRY_RFB, **(schema.countries or {})},
            "schema_version": schema.schema_version,
            "status": "HOMOLOGADO" if schema.is_homologated else "PRELIMINAR",
            "aviso": "" if schema.is_homologated else (
                f"Schema {schema.schema_version} não homologado — relatório "
                "PRELIMINAR."
            ),
        }

    def build(self) -> dict:
        yearend = date(self.year, 12, 31)
        ptax = PtaxService().get_rate(yearend)
        dirpf = self._dirpf_schema()

        assets = []
        cash = []
        exempt_accounts = []
        # RF-PER-004: acumuladores por conta para atribuição proporcional
        # ao contribuinte (contas conjuntas / de terceiros).
        attrib = {}
        prev_yearend = date(self.year - 1, 12, 31)
        for account in BrokerAccount.objects.filter(active=True):
            acc = attrib.setdefault(account.id, {"income_brl": Decimal(0), "custody_brl": Decimal(0)})
            balance_usd = CashLedgerService().balance(account, until=yearend)
            cash_brl = (balance_usd * ptax.rate).quantize(Decimal("0.01"))
            cash.append({
                "account": account,
                "balance_usd": balance_usd,
                "balance_brl": cash_brl,
            })
            # auditoria-fiscal 06: caixa atribuível também passa pela fatia
            # do contribuinte (mesma fonte de verdade)
            acc["cash_brl"] = (cash_brl * OwnershipService.taxpayer_share_factor(account)).quantize(Decimal("0.01"))
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
                # rendimentos e resultado de alienação são contabilizados para
                # a atribuição proporcional mesmo sem posição remanescente
                div_events = FinancialEvent.objects.filter(
                    account=account, asset=asset, active=True,
                    event_type__in=("DIVIDEND", "JUROS"),
                ).filter(
                    income_fiscal_year_q(self.year)
                ).prefetch_related("foreign_tax_payments")
                dividends_brl = Decimal(0)
                withholding_brl = Decimal(0)
                ptax_service = PtaxService()
                for ev in div_events:
                    fx = ev.fx_rate or Decimal(0)
                    # Auditoria-fiscal 04: gross = líquido + soma de TODOS os
                    # pagamentos de imposto do evento (sem `.first()`)
                    pagamentos = list(ev.foreign_tax_payments.all())
                    gross_usd = ev.amount_usd + sum((p.tax_usd for p in pagamentos), Decimal(0))
                    dividends_brl += gross_usd * fx
                    # imposto pago no exterior: PTAX COMPRA na data de cada pagamento
                    for pagamento in pagamentos:
                        fx_tax = fx_imposto_exterior(ev, pagamento, ptax_service)
                        withholding_brl += pagamento.tax_usd * fx_tax
                gains_brl = Decimal(0)
                losses_brl = Decimal(0)
                for r in PositionService().realized(account, asset, until=yearend):
                    if r["event"].trade_date.year == self.year:
                        if r["gain_brl"] > 0:
                            gains_brl += r["gain_brl"]
                        else:
                            losses_brl += -r["gain_brl"]
                # auditoria-fiscal 06: MESMA fonte de verdade que o engine —
                # os fatos exibidos já são atribuídos ao contribuinte
                fator = OwnershipService.taxpayer_share_factor(account)
                dividends_brl *= fator
                withholding_brl *= fator
                gains_brl *= fator
                losses_brl *= fator
                acc["income_brl"] += (dividends_brl + gains_brl - losses_brl).quantize(Decimal("0.01"))
                # P0 titularidade no patrimônio: a custódia acumulada para a
                # atribuição usa a MESMA fatia do contribuinte que rendimentos
                # e ganhos (OwnershipService) — o valor integral da conta é
                # exibido como referência, jamais como valor fiscal do
                # contribuinte.
                acc["custody_brl"] += (pos["cost_brl_total"] * fator).quantize(Decimal("0.01"))
                if pos["quantity"]:
                    prev = PositionService().position(account, asset, until=prev_yearend)
                    cost_usd_total = (pos["avg_cost_usd"] * pos["quantity"]).quantize(Decimal("0.01"))
                    ptax_media = (
                        pos["cost_brl_total"] / cost_usd_total
                        if cost_usd_total else Decimal(0)
                    ).quantize(Decimal("0.00000001"))
                    assets.append({
                        "asset": asset, **pos,
                        "share_pct": account.ownership_share,
                        "cost_brl_attrib": (pos["cost_brl_total"] * fator).quantize(Decimal("0.01")),
                        "prev_cost_brl_attrib": (prev["cost_brl_total"] * fator).quantize(Decimal("0.01")),
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
                # não aproveitado = elegível − utilizado (o inelegível é
                # reportado à parte; achado P0 do auditor)
                "credit_unused_brl": (d["credit_eligible_brl"] - d["credit_used"]).quantize(Decimal("0.01")),
                "fx_income": d["fx_income"],
                "fx_tax": d["fx_tax"],
                "tax_payment_date": d["tax_payment_date"],
                "credit_eligible": d.get("credit_eligible", True),
            }
            for d in income["detail"] if d["withholding_brl"] > 0
        ]

        profile = Profile.objects.first()
        snapshot = AnnualAssessment.objects.filter(year=self.year).first()
        prev_snapshot = AnnualAssessment.objects.filter(year=self.year - 1).first()
        # RF-PER-004: demonstração da fatia do contribuinte. Auditoria-fiscal
        # 06: a atribuição já foi aplicada no cálculo (OwnershipService) —
        # aqui é só exibição, sem re-dividir (nada de dupla atribuição).
        ownership_attribution = []
        for account in BrokerAccount.objects.filter(active=True):
            acc = attrib.get(account.id, {"income_brl": Decimal(0), "custody_brl": Decimal(0), "cash_brl": Decimal(0)})
            ownership_attribution.append({
                "account": account,
                "ownership_type": account.ownership_type,
                "share_pct": account.ownership_share,
                "income_brl_attrib": acc["income_brl"].quantize(Decimal("0.01")),
                "custody_brl_attrib": acc["custody_brl"].quantize(Decimal("0.01")),
                "cash_brl_attrib": acc.get("cash_brl", Decimal(0)).quantize(Decimal("0.01")),
            })
        return {
            "ownership_attribution": ownership_attribution,
            "cbe": CbeService(self.year).evaluate(),
            "high_income": HighIncomeService(self.year).evaluate(),
            "darf": DarfGuideService(self.year).build(
                tax_due_brl=TaxEngine(self.year).compute()["tax_due_brl"]
            ),
            "dirpf": {
                "schema_version": dirpf["schema_version"],
                "status": dirpf["status"],
                "aviso": dirpf.get("aviso", ""),
            },
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
                 "share_pct": a["share_pct"],
                 "cost_brl_attrib": a["cost_brl_attrib"],
                 "prev_cost_brl_attrib": a["prev_cost_brl_attrib"],
                 "prev_cost_brl": a["prev_cost_brl"], "cost_usd_total": a["cost_usd_total"],
                 "ptax_media": a["ptax_media"], "dividends_brl": a["dividends_brl"],
                 "withholding_brl": a["withholding_brl"], "gains_brl": a["gains_brl"],
                 "losses_brl": a["losses_brl"],
                 "grupo_codigo": dirpf["groups"].get(a["asset"].asset_type, "03/99"),
                 "country_code_rfb": dirpf["countries"].get(a["asset"].country_code, ("", ""))[0],
                 "country_name": dirpf["countries"].get(a["asset"].country_code, ("", a["asset"].country_code))[1],
                 "cost_usd_text": f"US$ {a['cost_usd_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                 "discriminacao": (
                     f"{a['quantity']} de {a['asset'].description} ({a['asset'].ticker}), "
                     f"custo total de aquisição US$ {a['cost_usd_total']:,.2f}, "
                     f"custo fiscal R$ {a['cost_brl_total']:,.2f}"
                     + (
                         f" (fatia do contribuinte {a['share_pct']:,.0f}%: "
                         f"R$ {a['cost_brl_attrib']:,.2f})"
                         if a["cost_brl_attrib"] != a["cost_brl_total"] else ""
                     )
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
