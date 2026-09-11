"""CBE — Declaração de Capitais Brasileiros no Exterior (RF-CBE-001..007).

Auditoria-fiscal 07 (CBE v2): a apuração reflete o balanço real dos capitais.

Res. BCB nº 279/2022 (que regulamenta a Lei nº 14.286/2021):
- data-base 31/12: capitais ≥ US$ 1.000.000,00 → CBE anual;
- datas-base 31/03, 30/06 e 30/09: capitais ≥ US$ 100.000.000,00 →
  declaração trimestral (cada data-base apurada INDEPENDENTEMENTE —
  o patrimônio de 31/12 nunca decide a obrigação trimestral).

Caixa: saldo do ledger de caixa (CashLedgerService — considera BUY, SELL,
dividendos, juros, taxas), nunca soma parcial de aportes/retiradas (que
duplicava patrimônio: a compra não reduzia o caixa e o ativo entrava por
custo médio).

Patrimônio: valor na data-base informado e CONFIRMADO pelo contribuinte
(AssetValuation) — sem valor confirmado, o item fica UNDETERMINED em vez
de chutar. Valores atribuíveis respeitam a participação do titular
(OwnershipService, auditoria-fiscal 06).
"""
from datetime import date
from decimal import Decimal

from fiscal.models import AssetValuation, Profile
from ledger.cash import CashLedgerService
from ledger.models import Asset, BrokerAccount
from ledger.ownership import OwnershipService
from ledger.position import PositionService

LIMITE_ANUAL_USD = Decimal(1_000_000)
LIMITE_TRIMESTRAL_USD = Decimal(100_000_000)

DATA_BASES_TRIMESTRAIS = ((3, 31), (6, 30), (9, 30))


class CbeService:
    def __init__(self, year: int):
        self.year = year

    def _data_base(self) -> date:
        return date(self.year, 12, 31)

    def evaluate(self) -> dict:
        """Apuração v2: anual em 31/12 + três datas-base trimestrais
        independentes (cada uma com seu próprio total e status)."""
        anual = self._evaluate_data_base(self._data_base(), periodicidade="anual")
        trimestrais = [
            self._evaluate_data_base(date(self.year, m, d), periodicidade="trimestral")
            for (m, d) in DATA_BASES_TRIMESTRAIS
        ]
        return {
            # chaves de compatibilidade com o relatório (anual = 31/12)
            "status": anual["status"],
            "quarterly": any(t["status"] == "CBE_REQUIRED" for t in trimestrais),
            "total_usd": anual["total_usd"],
            "annual": anual,
            "quarterly_bases": trimestrais,
            "legal_basis": "Res. BCB nº 279/2022 (Lei nº 14.286/2021)",
        }

    def _evaluate_data_base(self, data_base: date, periodicidade: str) -> dict:
        # auditoria-fiscal 06: valores atribuíveis respeitam a fatia do
        # titular EM CADA CONTA (a participação é por conta, não global)
        caixa_usd = sum(
            (
                CashLedgerService().balance(conta, until=data_base)
                * OwnershipService.taxpayer_share_factor(conta)
                for conta in BrokerAccount.objects.filter(active=True)
            ),
            Decimal(0),
        ).quantize(Decimal("0.01"))
        patrimonial, pendentes = self._patrimonio_usd(data_base)

        resultado = {
            "data_base": data_base,
            "periodicidade": periodicidade,
            "cash_usd": caixa_usd,
            "assets_usd": patrimonial if not pendentes else None,
            "missing_valuations": pendentes,
        }
        if pendentes:
            # sem valor confirmado na data-base: UNDETERMINED — nunca usar
            # custo médio como proxy patrimonial (auditoria-fiscal 07)
            resultado.update({
                "status": "CBE_UNDETERMINED",
                "total_usd": None,
                "quarterly": False,
                "message": (
                    "Ativos em custódia sem valor de mercado confirmado na "
                    "data-base — informe o valor (AssetValuation) para apurar "
                    "a obrigação de CBE."
                ),
            })
            return resultado
        total = (caixa_usd + patrimonial).quantize(Decimal("0.01"))
        if periodicidade == "trimestral":
            limite, quarterly = LIMITE_TRIMESTRAL_USD, True
        else:
            limite, quarterly = LIMITE_ANUAL_USD, False
        if total >= limite:
            status = "CBE_REQUIRED"
        else:
            profile = Profile.objects.first()
            completo = bool(profile and profile.external_assets_declared_complete)
            status = "CBE_NOT_REQUIRED" if completo else "CBE_UNDETERMINED"
        resultado.update({"status": status, "total_usd": total, "quarterly": quarterly})
        return resultado

    def _patrimonio_usd(self, data_base: date) -> tuple[Decimal, list]:
        """Custódia: valor de mercado CONFIRMADO na data-base, por conta+ativo.

        Sem valor confirmado → pendência (item UNDETERMINED), nunca custo
        médio como proxy. Devolve (total confirmado, pendências)."""
        total = Decimal(0)
        pendentes = []
        posicoes = []
        for conta in BrokerAccount.objects.filter(active=True):
            for asset in Asset.objects.filter(events__account=conta, events__active=True, events__trade_date__lte=data_base).distinct():
                pos = self._posicao(conta, asset, data_base)
                if pos > 0:
                    posicoes.append((conta, asset, pos))
        for conta, asset, qty in posicoes:
            valor = AssetValuation.objects.filter(
                account=conta, asset=asset, reference_date=data_base,
            ).first()
            if valor and valor.confirmed:
                total += valor.value_usd * OwnershipService.taxpayer_share_factor(conta)
            else:
                pendentes.append({
                    "account": conta, "asset": asset, "quantity": qty,
                    "confirmed": bool(valor),
                })
        return total, pendentes

    def _posicao(self, conta, asset, data_base):
        return PositionService().position(conta, asset, until=data_base)["quantity"]