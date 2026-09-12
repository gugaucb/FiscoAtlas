from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from fiscal.date_rules import TaxDateResolver, fiscal_year_q, income_fiscal_year_q
from fiscal.foreign_tax import ForeignTaxCreditService
from fiscal.losses import LossLedgerService
from fiscal.models import AnnualAssessment, LossRecord, Profile, TaxRule
from fx.service import PtaxService
from ledger.models import Asset, FinancialEvent
from ledger.ownership import OwnershipService
from ledger.position import PositionService

ZERO = Decimal("0.00")

# Regimes tributários não cobertos pela apuração de aplicação financeira
# direta (RF-AST-009/RF-VAL-002): exigem regime próprio.
BLOCKED_ASSET_TYPES = ("CONTROLLED_ENTITY", "TRUST", "UNKNOWN")


def _pagamentos_por_evento(events):
    """Mapa event_id → list[ForeignTaxPayment].

    Auditoria-fiscal 04: um evento pode ter VÁRIOS pagamentos de imposto
    (ex.: retenção federal + estadual dos EUA) — todos entram no cálculo."""
    from ledger.models import ForeignTaxPayment
    ev_ids = [ev.id for ev in events]
    out: dict = {}
    for p in ForeignTaxPayment.objects.filter(financial_event_id__in=ev_ids):
        out.setdefault(p.financial_event_id, []).append(p)
    return out


def fx_imposto_exterior(ev, pagamento, ptax_service) -> Decimal:
    """PTAX COMPRA na data documental do pagamento (Lei 14.754/2023, art. 4º §2º).

    Fallback para o fx do evento somente quando não há pagamento (imposto zero)."""
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
        # Ticket 28 (P0 do auditor): consolidação do Loss Ledger acontece no
        # FECHAMENTO — devolve compensações do próprio ano (refechamento
        # idempotente), sincroniza os registros com o resultado fiscal ATUAL
        # das alienações e só então consome FIFO (tudo em uma transação).
        with transaction.atomic():
            LossLedgerService.revert_compensations(year)
            LossLedgerService.sync_year(year, result["resultados_alienacao"])
            # RF-LOS-007: consolida a compensação FIFO no ledger (idempotente)
            LossLedgerService.apply_compensation(year, result["income_brl"])
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
                    "event_id": d["event"].id if d.get("event") else None,
                    "kind": d["kind"],
                    "description": d.get("description") or str(d["event"]),
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
            (Q(events__active=True) & fiscal_year_q(self.year, prefix="events__"))
            | (Q(events__corrected_by__active=True) & fiscal_year_q(self.year, prefix="events__corrected_by__"))
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

    def _resultados_alienacao(self) -> list:
        """Resultados fiscais das alienações do ano (fato atribuído ao
        contribuinte), SEM efeitos persistentes — fonte do compute e da
        sincronização do Loss Ledger no fechamento (ticket 28)."""
        gain_q = Q(event_type__in=("SELL", "CASH_IN_LIEU"), trade_date__year=self.year)
        sells = list(
            FinancialEvent.objects.filter(gain_q, active=True)
            .select_related("asset").order_by("trade_date", "id")
        )
        realized_idx = {}
        account_ids = {ev.account_id for ev in sells}
        asset_ids = {ev.asset_id for ev in sells if ev.asset_id}
        for account_id in account_ids:
            for asset_id in asset_ids:
                for r in PositionService().realized(account_id, asset_id):
                    if r["event"].trade_date.year == self.year:
                        realized_idx[r["event"].id] = r
        out = []
        for ev in sells:
            r = realized_idx.get(ev.id)
            if r is None:
                continue
            fator = OwnershipService.taxpayer_share_factor(ev.account)
            out.append({
                "event": ev,
                "gain_brl": (r["gain_brl"] * fator).quantize(Decimal("0.01")),
                "sale_brl": r["sale_brl"], "cost_sold_brl": r["cost_sold_brl"],
            })
        return out

    def compute(self) -> dict:
        self._exigir_residente_fiscal()
        self._bloquear_ativos_nao_cobertos()
        rule = TaxRule.objects.for_year(self.year)
        rate = Decimal(rule.brackets[-1]["rate"])
        # Auditoria-fiscal 10: o ano fiscal difere por componente —
        # ganhos de alienação: data da operação (trade_date é o fato gerador
        # correto no IRPF); rendimentos: data de RECEBIMENTO. Sem fallback
        # silencioso: rendimento sem income_receipt_date (legado) bloqueia.
        gain_q = Q(event_type__in=("SELL", "CASH_IN_LIEU"), trade_date__year=self.year)
        income_q = income_fiscal_year_q(self.year)
        events = list(
            FinancialEvent.objects.filter(gain_q | income_q, active=True)
            .select_related("asset").order_by("trade_date", "id")
        )
        # Ticket 28: resultados de alienação calculados SEM efeito
        # persistente — a gravação no Loss Ledger pertence ao fechamento.
        resultados = self._resultados_alienacao()
        resultados_por_evento = {r["event"].id: r for r in resultados}

        detail = []
        income = ZERO
        loss = ZERO
        credit_potencial = ZERO
        ineligible_foreign_tax = ZERO
        pagamentos = _pagamentos_por_evento(events)
        # RF-FTC-009: estornos de retenção do ano reduzem o crédito do rendimento
        # de origem (a retenção efetiva é a que sobrevive ao 1042-S)
        refunds_por_origem = {}
        refunds = FinancialEvent.objects.filter(
            active=True, trade_date__year=self.year, event_type="WITHHOLDING_REFUND",
            refund_of__isnull=False,
        ).select_related("refund_of")
        for refund in refunds:
            refund_brl = refund.amount_usd * (refund.fx_rate or ZERO) * OwnershipService.taxpayer_share_factor(refund.refund_of.account)
            refunds_por_origem[refund.refund_of_id] = (
                refunds_por_origem.get(refund.refund_of_id, ZERO) + refund_brl
            )
        for refund in refunds:
            detail.append({
                "event": refund, "kind": "withholding_refund",
                "gross_brl": ZERO, "withholding_brl": ZERO, "credit_used": ZERO,
                "description": (
                    f"Estorno de retenção (RF-FTC-009) — {refund.refund_of} "
                    f"({refund.refund_of.trade_date.year})"
                ),
            })
        for ev in events:
            fx = ev.fx_rate or ZERO
            # RF-PER-003 / auditoria-fiscal 06: a titularidade entra no
            # CÁLCULO (não só na exibição) — fatos fiscais da conta são
            # atribuídos ao contribuinte pela fatia dele.
            fator = OwnershipService.taxpayer_share_factor(ev.account)
            if ev.event_type in ("SELL", "CASH_IN_LIEU"):
                res = resultados_por_evento.get(ev.id)
                if res is None:
                    continue
                gain_brl = res["gain_brl"]
                gross_brl = gain_brl if gain_brl > 0 else ZERO
                if gain_brl < 0:
                    loss += -gain_brl
                income += gross_brl
                detail.append({
                    "event": ev, "kind": "gain/loss", "gross_brl": gross_brl,
                    "sale_brl": res["sale_brl"], "cost_sold_brl": res["cost_sold_brl"],
                    "withholding_brl": ZERO, "credit_used": ZERO,
                })
            else:  # DIVIDEND, JUROS
                if ev.income_receipt_date is None:
                    raise ValidationError(
                        f"Rendimento {ev} (id {ev.id}) sem data de recebimento "
                        "registrada — dados legados precisam de income_receipt_date "
                        "antes da apuração (sem fallback silencioso para a data da operação)."
                    )
                # Auditoria-fiscal 10: fx do evento é a PTAX VENDA da data de
                # RECEBIMENTO (resolvida no capture pela data fiscal — ver
                # EventService.record); o resolver valida a data existente.
                TaxDateResolver().resolve(event=ev, date_rule="INCOME_RECEIPT_DATE")
                pagamentos_ev = pagamentos.get(ev.id, [])
                # Auditoria-fiscal 04: gross = rendimento líquido + soma de
                # TODOS os pagamentos de imposto do evento (0..N).
                gross_usd = ev.amount_usd + sum((p.tax_usd for p in pagamentos_ev), ZERO)
                gross_brl = (gross_usd * fx * fator).quantize(Decimal("0.01"))
                income += gross_brl
                # imposto pago no exterior: PTAX COMPRA na data de CADA pagamento
                # (retido na parcela do contribuinte — titularidade)
                eligible_wh = ZERO
                ineligible_wh = ZERO
                fx_tax_last = fx
                tax_date_last = ev.trade_date
                for pagamento in pagamentos_ev:
                    fx_tax = fx_imposto_exterior(ev, pagamento, PtaxService())
                    wh = (pagamento.tax_usd * fx_tax * fator).quantize(Decimal("0.01"))
                    fx_tax_last = fx_tax
                    tax_date_last = pagamento.foreign_tax_payment_date
                    # elegibilidade (RF-FTC-002/003): por pagamento, decisão
                    # centralizada no ForeignTaxCreditService (ticket 05).
                    if ForeignTaxCreditService.is_eligible(pagamento):
                        eligible_wh += wh
                    else:
                        ineligible_wh += wh
                wh_brl = eligible_wh + ineligible_wh
                # RF-FTC-009: deduz estornos do próprio ano (retenção efetiva),
                # primeiro da parcela elegível
                refund_brl = refunds_por_origem.get(ev.id, ZERO)
                if refund_brl > 0:
                    deducao = min(refund_brl, eligible_wh)
                    eligible_wh -= deducao
                    refund_restante = refund_brl - deducao
                    ineligible_wh = max(ineligible_wh - refund_restante, ZERO)
                wh_brl = eligible_wh + ineligible_wh
                # crédito potencial: limite de 15% por rendimento — o
                # aproveitamento EFETIVO é limitado depois, pelo IR devido
                # do ano (após prejuízos), achado P0 do auditor
                potencial = min(eligible_wh, (gross_brl * rate).quantize(Decimal("0.01")))
                credit_potencial += potencial
                ineligible_foreign_tax += ineligible_wh
                detail.append({
                    "event": ev, "kind": ev.event_type.lower(), "gross_brl": gross_brl,
                    "withholding_brl": wh_brl,
                    "credit_eligible_brl": eligible_wh,
                    "credit_potential": potencial,
                    "credit_used": potencial,  # ajustado pelo teto global abaixo
                    "credit_eligible": eligible_wh > 0,
                    "fx_income": fx, "fx_tax": fx_tax_last,
                    "tax_payment_date": tax_date_last,
                })

        # Prejuízo herdado de anos anteriores (P&R IRPF: prejuízos são
        # compensáveis nos anos seguintes). Ticket 29 (P0 do auditor):
        # reconstrução HISTÓRICA — saldo no início do ano apurado
        # (amount_brl − compensações de anos anteriores), NUNCA o
        # remaining_brl mutável: o resultado do ano não muda porque
        # compensações ocorreram nele ou depois dele. Fallback legado:
        # scalar do AnnualAssessment anterior (quando o ledger não conhece
        # os anos anteriores).
        registros = LossLedgerService.open_records_at_start_of(self.year)
        if registros:
            loss_inherited = sum((r["saldo_brl"] for r in registros), ZERO)
        elif not LossRecord.objects.filter(origin_year__lte=self.year - 1).exists():
            # fallback legado só quando o ledger NÃO conhece os anos
            # anteriores; se houver registros (mesmo filtrados — ex. perda
            # de evento corrigido, achado P0 do auditor), o scalar do
            # AnnualAssessment anterior não pode reverter a exclusão.
            prev = AnnualAssessment.objects.filter(year=self.year - 1).first()
            loss_inherited = prev.loss_carryforward_brl if prev else ZERO
        else:
            loss_inherited = ZERO
        total_loss_available = loss + loss_inherited

        taxable = max(income - total_loss_available, ZERO)
        excess_loss = max(total_loss_available - income, ZERO)
        tax = (taxable * rate).quantize(Decimal("0.01"))
        # Achado P0 do auditor: o crédito aproveitado não pode exceder o IR
        # devido do ano (após prejuízos). Potencial por rendimento é uma
        # coisa; o utilizado é o potencial limitado GLOBAMENTE pelo IR devido.
        credit_used_total = min(credit_potencial, tax)
        restante_cap = credit_used_total
        for d in detail:
            potencial = d.get("credit_potential")
            if potencial:
                uso = min(potencial, restante_cap)
                d["credit_used"] = uso
                restante_cap -= uso
        credit_unused = credit_potencial - credit_used_total
        for r in registros:
            if r["saldo_brl"] > 0:
                registro = r["record"]
                detail.insert(0, {
                    "event": None, "kind": "loss_carryforward",
                    "gross_brl": -r["saldo_brl"],
                    "description": (
                        f"R$ {r['saldo_brl']} originados em {registro.origin_year}"
                        + (f" — {registro.description}" if registro.description else "")
                    ),
                    "withholding_brl": ZERO, "credit_used": ZERO,
                })
        if loss_inherited > 0 and not registros:
            detail.insert(0, {
                "event": None, "kind": "loss_carryforward",
                "gross_brl": -loss_inherited,
                "description": f"Prejuízo a compensar de {self.year - 1}",
                "withholding_brl": ZERO, "credit_used": ZERO,
            })
        return {
            "resultados_alienacao": resultados,
            "income_brl": income,
            "loss_brl": loss,
            "loss_inherited_brl": loss_inherited,
            "taxable_brl": taxable,
            "tax_brl": tax,
            "withholding_credit_brl": credit_used_total,
            "credit_potential_brl": credit_potencial,
            "credit_unused_brl": credit_unused,
            "ineligible_foreign_tax_brl": ineligible_foreign_tax,
            "tax_due_brl": tax - credit_used_total,
            "loss_carryforward_brl": excess_loss,
            "detail": detail,
            "rule": rule,
        }
