from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.db import transaction

from fx.service import PtaxService
from ledger.models import Asset, FinancialEvent, ForeignTaxPayment
from ledger.position import PositionService

TOL = Decimal("0.01")

# Campos que pertencem ao ForeignTaxPayment, não ao FinancialEvent
FOREIGN_TAX_FIELDS = (
    "foreign_tax_payment_date", "confirm_same_day", "country_code",
    "jurisdiction_level", "tax_type", "capture_method",
    "date_evidence_source", "source_document_id", "source_reference",
)


def resolve_current_event_base_date(data: dict) -> date:
    """Data base do evento para componentes do rendimento (compatibilidade do
    modelo atual: único campo de data é trade_date). Quando o TaxDateResolver
    existir (ticket 02), esta resolução passa a ser guiada por TaxRule.date_rule."""
    return data["trade_date"]


class EventService:
    def __init__(self, ptax: PtaxService | None = None):
        self.ptax = ptax or PtaxService()

    def _ptax_rate(self, trade_date) -> Decimal:
        return self.ptax.get_rate(trade_date).rate

    def record(self, data: dict) -> FinancialEvent:
        etype = data["event_type"]
        qty, price = data.get("quantity"), data.get("price_usd")
        fee = data.get("fee_usd") or Decimal(0)
        tax = data.get("tax_usd") or Decimal(0)

        # RF-AST-003: ativo deve existir; sem auto-criação silenciosa.
        if not data.get("asset") and data.get("asset_ticker"):
            ticker = str(data["asset_ticker"]).strip().upper()
            try:
                data["asset"] = Asset.objects.get(ticker=ticker, active=True)
            except Asset.DoesNotExist:
                raise ValueError(f"Ativo {ticker} não cadastrado; cadastre-o explicitamente antes do lançamento.")
            data.pop("asset_ticker")

        if etype == "JUROS" and not data["account"].is_interest_bearing:
            raise ValueError("JUROS só é válido em conta remunerada; conta não remunerada")
        if etype in ("BUY", "SELL") and (not qty or not price or qty <= 0 or price <= 0):
            raise ValueError("quantity e price_usd devem ser positivos para BUY/SELL")
        if etype in ("STOCK_SPLIT", "REVERSE_SPLIT"):
            de, para = data.get("split_ratio_from"), data.get("split_ratio_to")
            if not de or not para or de <= 0 or para <= 0:
                raise ValueError("Informe a razão do split (split_ratio_from e split_ratio_to).")
        if etype == "BUY":
            expected = -(qty * price + fee)
        elif etype == "SELL":
            expected = qty * price - fee
        elif etype == "DIVIDEND":
            expected = data.get("per_share_usd", Decimal(0)) * qty - tax
        elif etype in ("STOCK_SPLIT", "REVERSE_SPLIT"):
            expected = Decimal(0)
        elif etype == "CASH_IN_LIEU":
            expected = data["amount_usd"]
        else:  # APORTE, WITHDRAWAL, JUROS, FEE, TAX_WITHHELD
            expected = data["amount_usd"]
            if etype in ("WITHDRAWAL", "FEE", "TAX_WITHHELD"):
                # saídas de caixa: converte para negativo independente do sinal informado
                expected = -abs(expected)

        informed = data.get("amount_usd")
        if etype in ("BUY", "SELL", "DIVIDEND") and informed is not None and abs(informed - expected) > TOL:
            raise ValueError(f"amount_usd diverge do calculado: esperado {expected}")

        if etype in ("SELL", "CASH_IN_LIEU"):
            pos = PositionService().position(data["account"], data["asset"])
            if pos["quantity"] < qty:
                raise ValueError(f"posição insuficiente: {pos['quantity']} < {qty}")

        manual_rate = data.pop("ptax_manual", None)
        manual_reason = data.pop("ptax_reason", None)
        if manual_rate:
            rate = self.ptax.override(
                data["trade_date"], Decimal(str(manual_rate)), manual_reason or ""
            ).rate
        else:
            rate = self._ptax_rate(data["trade_date"])
        if data.get("corrects"):
            data["corrects"].active = False
            data["corrects"].save()

        tax = data.get("tax_usd") or Decimal(0)
        pagamento = self._dados_imposto_exterior(data, tax)
        fields = {k: v for k, v in data.items() if k not in ("amount_usd", "corrects", "per_share_usd", *FOREIGN_TAX_FIELDS)}
        fields["fee_usd"] = fields.get("fee_usd") or Decimal(0)
        fields["tax_usd"] = fields.get("tax_usd") or Decimal(0)
        with transaction.atomic():
            evento = FinancialEvent.objects.create(
                **fields,
                corrects=data.get("corrects"),
                amount_usd=expected,
                fx_rate=rate,
                amount_brl=(expected * rate).quantize(Decimal("0.00000001")),
            )
            if pagamento:
                ForeignTaxPayment.objects.create(financial_event=evento, **pagamento)
        return evento

    def _dados_imposto_exterior(self, data: dict, tax: Decimal) -> dict | None:
        """Valida e extrai os fatos do imposto pago no exterior.

        Sem fallback silencioso de data: exige a data documental do pagamento
        ou confirmação explícita de que coincide com a data do rendimento
        (com evidência documental — a igualdade por si só não é evidência).
        """
        if not tax or tax <= 0:
            return None
        data_pgto = data.get("foreign_tax_payment_date")
        evidencia = data.get("date_evidence_source") or "UNKNOWN"
        if data_pgto is None:
            if not data.get("confirm_same_day"):
                raise ValueError(
                    "Informe a data de pagamento do imposto no exterior "
                    "(foreign_tax_payment_date) ou confirme que coincide com "
                    "a data do rendimento (confirm_same_day)."
                )
            if evidencia == "UNKNOWN":
                raise ValueError(
                    "A igualdade de datas exige evidência documental "
                    "(date_evidence_source != UNKNOWN)."
                )
            data_pgto = resolve_current_event_base_date(data)
        return {
            "tax_usd": tax,
            "foreign_tax_payment_date": data_pgto,
            "country_code": data.get("country_code") or "",
            "jurisdiction_level": data.get("jurisdiction_level") or "UNKNOWN",
            "tax_type": data.get("tax_type") or "UNKNOWN",
            "capture_method": data.get("capture_method") or "MANUAL",
            "date_evidence_source": evidencia,
            "source_document_id": data.get("source_document_id") or "",
            "source_reference": data.get("source_reference") or "",
        }


class BrokerTransferService:
    """RF-CST-003/004: transferência de ativos/caixa entre contas do mesmo
    titular não é alienação — registra par de pontas (mesmo transfer_pair_id)
    e transporta quantidade + custo histórico BRL integralmente."""

    def __init__(self, ptax: PtaxService | None = None):
        self.ptax = ptax or PtaxService()

    def _ptax_rate(self, trade_date) -> Decimal:
        return self.ptax.get_rate(trade_date).rate

    def record(self, out_account, in_account, trade_date, asset=None,
               quantity=None, amount_usd=None) -> tuple:
        if out_account == in_account:
            raise ValueError("conta de origem e destino devem ser distintas.")
        rate = self._ptax_rate(trade_date)
        pair_id = uuid4()
        if asset:
            pos = PositionService().position(out_account, asset)
            if quantity is None or quantity <= 0 or pos["quantity"] < quantity:
                raise ValueError(
                    f"posição insuficiente: {pos['quantity']} < {quantity}"
                )
            avg_usd = pos["avg_cost_usd"]
            cost_usd = (avg_usd * quantity).quantize(Decimal("0.00000001"))
            cost_brl = (pos["cost_brl_total"] * quantity / pos["quantity"]).quantize(Decimal("0.00000001"))
            base = dict(asset=asset, quantity=quantity, price_usd=None,
                        fee_usd=Decimal(0), tax_usd=Decimal(0),
                        transfer_pair_id=pair_id, trade_date=trade_date)
            out = {**base, "event_type": "BROKER_TRANSFER_OUT", "account": out_account}
            inp = {**base, "event_type": "BROKER_TRANSFER_IN", "account": in_account}
            out["amount_usd"], inp["amount_usd"] = cost_usd, cost_usd
            out["amount_brl"], inp["amount_brl"] = cost_brl, cost_brl
        else:
            if not amount_usd or amount_usd <= 0:
                raise ValueError("informe quantity (ativo) ou amount_usd (caixa).")
            out = dict(event_type="BROKER_TRANSFER_OUT", account=out_account,
                       trade_date=trade_date, amount_usd=amount_usd,
                       fee_usd=Decimal(0), tax_usd=Decimal(0),
                       transfer_pair_id=pair_id)
            inp = dict(event_type="BROKER_TRANSFER_IN", account=in_account,
                       trade_date=trade_date, amount_usd=amount_usd,
                       fee_usd=Decimal(0), tax_usd=Decimal(0),
                       transfer_pair_id=pair_id)
            out["amount_brl"] = inp["amount_brl"] = (amount_usd * rate).quantize(Decimal("0.00000001"))
        out["fx_rate"] = inp["fx_rate"] = rate
        with transaction.atomic():
            saida = FinancialEvent.objects.create(**out)
            entrada = FinancialEvent.objects.create(**inp)
        return saida, entrada
