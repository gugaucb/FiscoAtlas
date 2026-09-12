"""Validador bloqueante do fechamento anual (RF-VAL-001..020).

O fechamento (`AnnualAssessment.confirmed = True`) só pode ocorrer se as
precondições fiscais do ano estiverem íntegras. Todas as violações são
coletadas e apresentadas juntas com mensagens explicativas — o usuário
corrige tudo de uma vez em vez de descobrir um erro por tentativa.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError

from fiscal.date_rules import fiscal_year_of_event, fiscal_year_q
from fiscal.models import AnnualAssessment, Profile
from ledger.models import Asset, FinancialEvent
from ledger.position import PositionService


class AnnualClosingValidator:
    def __init__(self, year: int):
        self.year = year

    def validate_or_raise(self):
        """Levanta ValidationError agregando todas as violações do ano."""
        self.violations = []
        self._checar_residencia()
        self._checar_ativos_unknown()
        self._checar_integridade_cambial()
        self._checar_vendas_acima_da_custodia()
        self._checar_transferencias_solitarias()
        self._checar_restituicoes_retroativas()
        self._checar_credito_exterior()
        if self.violations:
            raise ValidationError(self.violations)

    # ------------------------------------------------------------ RF-VAL-001
    def _checar_residencia(self):
        profile = Profile.objects.first()
        if profile is None or profile.tax_residency_status != "BRAZIL_RESIDENT":
            self.violations.append(
                "Residência fiscal não confirmada como residente pleno no Brasil "
                "(RF-VAL-001). Confirme em /perfil/ antes de fechar o ano."
            )

    # ------------------------------------------------------------ RF-VAL-002
    def _checar_ativos_unknown(self):
        qs = Asset.objects.filter(active=True, asset_type="UNKNOWN").filter(
            fiscal_year_q(self.year, prefix="events__"), events__active=True,
        ).distinct()
        for asset in qs:
            self.violations.append(
                f"Ativo {asset.ticker} com natureza jurídica UNKNOWN movimentado em "
                f"{self.year} (RF-VAL-002). Cadastre a natureza correta em "
                "ativos/novo/ — a apuração exige classificação legal."
            )

    # ------------------------------------------------------------ integridade
    def _checar_integridade_cambial(self):
        nulos = FinancialEvent.objects.filter(
            fiscal_year_q(self.year), active=True,
        ).filter(amount_brl__isnull=True) | FinancialEvent.objects.filter(
            fiscal_year_q(self.year), active=True, fx_rate__isnull=True,
        )
        if nulos.exists():
            self.violations.append(
                "Existem eventos ativos sem amount_brl ou fx_rate preenchidos "
                "(RF-VAL-003/004). A conversão cambial deve ser registrada em "
                "todos os eventos do ano."
            )

    # ------------------------------------------------------------ short sale
    def _checar_vendas_acima_da_custodia(self):
        eventos = FinancialEvent.objects.filter(
            active=True, trade_date__year=self.year, asset__isnull=False,
            event_type__in=("SELL", "CASH_IN_LIEU"),
        ).select_related("asset", "account")
        pares = {(ev.account_id, ev.asset_id) for ev in eventos}
        for account_id, asset_id in pares:
            for ev in eventos.filter(account_id=account_id, asset_id=asset_id):
                # custódia ANTERIOR à venda: position(until=trade_date) incluiria
                # a própria venda e liquidar 100% da posição seria "descoberto"
                pos = PositionService().position(
                    ev.account, ev.asset, until=ev.trade_date,
                    exclude_event_id=ev.id,
                )
                if ev.quantity > pos["quantity"]:
                    self.violations.append(
                        f"Venda de {ev.quantity} de {ev.asset.ticker} em "
                        f"{ev.trade_date:%d/%m/%Y} excede o saldo em custódia "
                        f"({pos['quantity']}) — venda a descoberto sem mecanismo "
                        "homologado não é apurável (RF-VAL-006)."
                    )

    # ------------------------------------------------------------ RF-CST-004
    def _checar_transferencias_solitarias(self):
        """CT-015: transferência sem ponta pareada (só IN ou só OUT com o
        mesmo transfer_pair_id) é inconsistência de registro."""
        from django.db.models import Count
        pares = (
            FinancialEvent.objects.filter(
                active=True, trade_date__year=self.year,
                event_type__in=("BROKER_TRANSFER_IN", "BROKER_TRANSFER_OUT"),
                transfer_pair_id__isnull=False,
            )
            .values("transfer_pair_id")
            .annotate(n=Count("id"))
            .filter(n__lt=2)
        )
        for p in pares:
            self.violations.append(
                "Transferência de custódia sem ponta pareada "
                f"(transfer_pair_id={p['transfer_pair_id']}) — inconsistência de "
                "registro (RF-CST-004). Registre a ponta correspondente."
            )

    # ------------------------------------------------------------ RF-FTC-009
    def _checar_restituicoes_retroativas(self):
        """CT-008: estorno de retenção em ano posterior ao do rendimento —
        se o ano de origem já foi fechado, exige retificação da DAA."""
        refunds = FinancialEvent.objects.filter(
            active=True, trade_date__year=self.year, event_type="WITHHOLDING_REFUND",
            refund_of__isnull=False,
        ).select_related("refund_of")
        for refund in refunds:
            # ano fiscal de origem: rendimentos (DIVIDEND/JUROS) pelo
            # recebimento — refund da trade_date é o fato gerador do refund
            origem = fiscal_year_of_event(refund.refund_of)
            if origem >= self.year:
                continue
            if AnnualAssessment.objects.filter(year=origem).exists():
                self.violations.append(
                    f"Restituição de imposto no exterior ({refund}) refere-se a "
                    f"rendimento de {origem}, cuja apuração já foi fechada — "
                    "necessária RETIFICAÇÃO da DAA/apuração de "
                    f"{origem} (RF-FTC-009; CT-008)."
                )

    # ------------------------------------------------------------ RF-VAL-008/009
    def _checar_credito_exterior(self):
        """Ticket 05 (auditoria-fiscal): retenção estrangeira > 15% do bruto é
        legítima (ex.: 30% dos EUA) e NÃO bloqueia — a lei limita o crédito
        aproveitável ao IR devido, e o excedente é segregado no relatório como
        não aproveitado (pago / elegível / aproveitado / não aproveitado). O
        único bloqueio aqui é pagamento com tratamento fiscal desconhecido
        (UNKNOWN), que exige classificação do usuário antes do fechamento."""
        from fiscal.foreign_tax import ForeignTaxCreditService
        from ledger.models import ForeignTaxPayment
        pagamentos = list(
            ForeignTaxPayment.objects.filter(
                financial_event__active=True,
            ).filter(
                fiscal_year_q(self.year, prefix="financial_event__"),
            ).select_related("financial_event")
        )
        desconhecidos = [p for p in pagamentos if not ForeignTaxCreditService.is_eligible(p)
                         and ForeignTaxCreditService.eligibility(p)[1].startswith("UNKNOWN")]
        for p in desconhecidos:
            self.violations.append(
                f"Imposto pago no exterior ({p}) com fatos fiscais desconhecidos "
                f"(jurisdição/tipo/evidência) — classifique em "
                f"/imposto-exterior/{p.pk}/editar/ antes de fechar o ano. "
                "Sem classificação explícita, o crédito não é aproveitado "
                "(sem regra fiscal silenciosa)."
            )
