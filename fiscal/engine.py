from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Q

from fiscal.date_rules import TaxDateResolver
from fiscal.models import AnnualAssessment, Profile, TaxRule
from fx.service import PtaxService
from ledger.models import Asset, FinancialEvent
from ledger.position import PositionService

ZERO = Decimal("0.00")

# Regimes tributários não cobertos pela apuração de aplicação financeira
# direta (RF-AST-009/RF-VAL-002): exigem regime próprio.
BLOCKED_ASSET_TYPES = ("CONTROLLED_ENTITY", "TRUST", "UNKNOWN")

# RF-FTC-002/003 (Lei 14.754/2023, art. 4º): a compensação decorre de
# reciprocidade de tratamento para tributos FEDERAIS sobre a renda.
# Imposto estadual/municipal (ex.: State/Local Income Tax dos EUA) não é
# elegível; países fora da lista também não geram crédito.
RECIPROCITY_COUNTRIES = {"US"}


def _pagamentos_por_evento(events):
    """Mapa event_id → ForeignTaxPayment (fatos do imposto no exterior)."""
    from ledger.models import ForeignTaxPayment
    ev_ids = [ev.id for ev in events]
    return {
        p.financial_event_id: p
        for p in ForeignTaxPayment.objects.filter(financial_event_id__in=ev_ids)
    }


def fx_imposto_exterior(ev, pagamento, ptax_service) -> Decimal:
    """PTAX COMPRA na data documental do pagamento (Lei 14.754/2023, art. 4º §2º).

    Fallback para o fx do evento somente quando o evento antecede a entidade
    ForeignTaxPayment (transição; ticket 03 remove event.tax_usd)."""
    if pagamento:
        data, quote = TaxDateResolver().resolve_ptax_request("FOREIGN_TAX", ev, pagamento)
        return ptax_service.get_rate(data, quote_type=quote).rate
    return ev.fx_rate or ZERO


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

    def _bloquear_ativos_nao_cobertos(self):
        qs = Asset.objects.filter(
            Q(events__active=True, events__trade_date__year=self.year)
            | Q(events__corrected_by__active=True, events__corrected_by__trade_date__year=self.year)
        ).distinct()
        bloqueados = [
            a.ticker for a in qs
            if a.asset_type in BLOCKED_ASSET_TYPES or a.is_controlled_entity
        ]
        if bloqueados:
            raise ValidationError(
                "Regime não coberto pela apuração de aplicação financeira direta: "
                f"ativo(s) {', '.join(sorted(bloqueados))} com natureza jurídica de "
                "entidade controlada, trust ou desconhecida. A apuração exige regime próprio."
            )

    def _exigir_residente_fiscal(self):
        """RF-PER-002 / RF-VAL-001: a apuração (Lei 14.754/2023) exige
        residência fiscal plena no Brasil — trava bloqueante."""
        profile = Profile.objects.first()
        if profile is None or profile.tax_residency_status != "BRAZIL_RESIDENT":
            raise ValidationError(
                "Contribuinte não qualificado como residente fiscal pleno no Brasil."
            )

    def compute(self) -> dict:
        self._exigir_residente_fiscal()
        self._bloquear_ativos_nao_cobertos()
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
        ineligible_foreign_tax = ZERO
        pagamentos = _pagamentos_por_evento(events)
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
                pagamento = pagamentos.get(ev.id)
                gross_usd = ev.amount_usd + ev.tax_usd
                gross_brl = (gross_usd * fx).quantize(Decimal("0.01"))
                income += gross_brl
                # imposto pago no exterior: PTAX COMPRA na data do pagamento
                fx_tax = fx_imposto_exterior(ev, pagamento, PtaxService())
                wh_brl = (ev.tax_usd * fx_tax).quantize(Decimal("0.01"))
                # elegibilidade (RF-FTC-002/003): só tributo federal de país
                # com reciprocidade; evento legado sem pagamento é mantido.
                if pagamento is not None:
                    eligible = (
                        pagamento.jurisdiction_level == "FEDERAL"
                        and pagamento.country_code in RECIPROCITY_COUNTRIES
                    )
                else:
                    eligible = True
                used = min(wh_brl, (gross_brl * rate).quantize(Decimal("0.01"))) if eligible else ZERO
                credit += used
                if not eligible:
                    ineligible_foreign_tax += wh_brl
                detail.append({
                    "event": ev, "kind": ev.event_type.lower(), "gross_brl": gross_brl,
                    "withholding_brl": wh_brl, "credit_used": used,
                    "credit_eligible": eligible,
                    "fx_income": fx, "fx_tax": fx_tax,
                    "tax_payment_date": pagamento.foreign_tax_payment_date if pagamento else ev.trade_date,
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
            "ineligible_foreign_tax_brl": ineligible_foreign_tax,
            "tax_due_brl": max(tax - credit, ZERO),
            "loss_carryforward_brl": excess_loss,
            "detail": detail,
            "rule": rule,
        }
