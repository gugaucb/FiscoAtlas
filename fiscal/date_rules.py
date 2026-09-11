"""Regra de data fiscal e tipo de PTAX por componente (Lei 14.754/2023).

Regra geral (art. 15): conversão pela cotação de VENDA do BCB na data do
fato gerador. Exceção (art. 4º §2º; IN RFB 2.180/2024, art. 12 §3º): o
imposto pago no exterior é convertido pela cotação de COMPRA na data do
pagamento — data própria, nunca presumida a partir do rendimento.

BUY/SELL da operação de mercado NÃO implicam BCB_BUY/BCB_SELL da cotação.
"""
from ledger.models import ForeignTaxPayment


# componente → (date_rule, quote_type BCB)
COMPONENT_RULES = {
    "ACQUISITION": ("ACQUISITION_DATE", "VENDA"),
    "DISPOSAL": ("DISPOSAL_DATE", "VENDA"),
    "INCOME": ("INCOME_RECEIPT_DATE", "VENDA"),
    "FOREIGN_TAX": ("FOREIGN_TAX_PAYMENT_DATE", "COMPRA"),
}

DATE_RULES = [
    ("ACQUISITION_DATE", "Data da aquisição"),
    ("DISPOSAL_DATE", "Data da alienação"),
    ("INCOME_RECEIPT_DATE", "Data do recebimento do rendimento"),
    ("FOREIGN_TAX_PAYMENT_DATE", "Data do pagamento do imposto no exterior"),
    ("REFERENCE_DATE", "Data de referência informada"),
]


class TaxDateResolver:
    """Resolve a data fiscal de um componente a partir da regra declarada."""

    def resolve(self, *, event, date_rule: str, pagamento: ForeignTaxPayment | None = None,
                reference_date=None):
        if date_rule == "FOREIGN_TAX_PAYMENT_DATE":
            if pagamento is None:
                raise ValueError(
                    "Componente FOREIGN_TAX exige o ForeignTaxPayment com a "
                    "data documental do pagamento do imposto."
                )
            return pagamento.foreign_tax_payment_date
        if date_rule == "REFERENCE_DATE":
            if reference_date is None:
                raise ValueError("REFERENCE_DATE exige a data de referência")
            return reference_date
        if date_rule == "INCOME_RECEIPT_DATE":
            # Auditoria-fiscal 10: o fato gerador do rendimento é o
            # recebimento — sem fallback silencioso para a trade_date.
            if event.income_receipt_date is None:
                raise ValueError(
                    "Rendimento sem data de recebimento registrada "
                    "(income_receipt_date) — informe a data documental do "
                    "recebimento antes de apurar."
                )
            return event.income_receipt_date
        # modelo atual: a data do fato gerador do evento é trade_date
        # (compra, alienação e recebimento de rendimento hoje coincidem no
        # campo); quando houver campos próprios, resolver aqui.
        return event.trade_date

    def resolve_ptax_request(self, component: str, event, pagamento: ForeignTaxPayment | None = None):
        """Devolve (data efetiva, quote_type) a pedir ao PtaxService."""
        if component not in COMPONENT_RULES:
            raise ValueError(f"Componente de câmbio desconhecido: {component}")
        date_rule, quote_type = COMPONENT_RULES[component]
        return self.resolve(event=event, pagamento=pagamento, date_rule=date_rule), quote_type
