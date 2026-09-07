"""Validador bloqueante do fechamento anual (RF-VAL-001..020).

O fechamento (`AnnualAssessment.confirmed = True`) só pode ocorrer se as
precondições fiscais do ano estiverem íntegras. Todas as violações são
coletadas e apresentadas juntas com mensagens explicativas — o usuário
corrige tudo de uma vez em vez de descobrir um erro por tentativa.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError

from fiscal.engine import TaxEngine
from fiscal.models import Profile
from ledger.models import Asset, FinancialEvent
from ledger.position import PositionService

# RF-FTC (Lei 14.754/2023, art. 4º): retenção estrangeira compensa até o IR
# devido; o excedente NÃO gera carryforward — bloqueia para revisão.
LIMITE_RETENCAO = Decimal("0.15")


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
        qs = Asset.objects.filter(
            active=True, asset_type="UNKNOWN", events__trade_date__year=self.year,
            events__active=True,
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
            active=True, trade_date__year=self.year,
        ).filter(amount_brl__isnull=True) | FinancialEvent.objects.filter(
            active=True, trade_date__year=self.year, fx_rate__isnull=True,
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
                pos = PositionService().position(ev.account, ev.asset, until=ev.trade_date)
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

    # ------------------------------------------------------------ RF-VAL-008/009
    def _checar_credito_exterior(self):
        try:
            resultado = TaxEngine(self.year).compute()
        except ValidationError:
            # o engine já reportou bloqueios próprios (residência, regime);
            # a verificação de crédito não acrescenta nada aqui.
            return
        retencao_total = Decimal(0)
        for d in resultado["detail"]:
            wh = d.get("withholding_brl", Decimal(0))
            if not wh:
                continue
            bruto = d.get("gross_brl", Decimal(0))
            if bruto > 0 and wh > bruto * LIMITE_RETENCAO:
                self.violations.append(
                    f"Imposto retido no exterior ({d['event']}) excede 15% do "
                    "rendimento bruto individual (RF-VAL-008). Revise o valor "
                    "documentado no extrato."
                )
            retencao_total += wh
        creditado = resultado["withholding_credit_brl"]
        if creditado < retencao_total:
            self.violations.append(
                "O crédito de imposto no exterior foi limitado ao IR devido — o "
                "excedente não gera carryforward para anos seguintes "
                "(RF-VAL-009; Lei 14.754/2023, art. 4º). Revise os documentos "
                "do imposto retido antes de fechar o ano."
            )
