from decimal import Decimal

import django.forms as forms
from ledger.models import DATE_EVIDENCE_SOURCES, JURISDICTION_LEVELS, TAX_TYPES, Asset, FinancialEvent
from ledger.foreign_tax_forms import ForeignTaxPaymentForm  # noqa: F401 (API única de formulários)

LABELS = {
    "event_type": "Tipo de evento",
    "account": "Conta",
    "asset_ticker": "Ativo (ticker)",
    "trade_date": "Data da operação",
    "quantity": "Quantidade",
    "price_usd": "Preço (USD)",
    "per_share_usd": "Valor por ação (USD)",
    "fee_usd": "Taxas (USD)",
    "tax_usd": "Imposto retido (USD)",
    "amount_usd": "Valor (USD)",
    "split_ratio_from": "Razão de (ações)",
    "split_ratio_to": "Razão para (ações)",
    "notes": "Observações",
}

REQUIRED_BY_TYPE = {
    "APORTE": ["account", "trade_date", "amount_usd"],
    "WITHDRAWAL": ["account", "trade_date", "amount_usd"],
    "JUROS": ["account", "trade_date", "amount_usd"],
    "FEE": ["account", "trade_date", "amount_usd"],
    "TAX_WITHHELD": ["account", "trade_date", "amount_usd"],
    "BUY": ["account", "asset_ticker", "trade_date", "quantity", "price_usd"],
    "SELL": ["account", "asset_ticker", "trade_date", "quantity", "price_usd"],
    "DIVIDEND": ["account", "asset_ticker", "trade_date", "quantity", "per_share_usd"],
    "STOCK_SPLIT": ["account", "asset_ticker", "trade_date", "split_ratio_from", "split_ratio_to"],
    "REVERSE_SPLIT": ["account", "asset_ticker", "trade_date", "split_ratio_from", "split_ratio_to"],
    "CASH_IN_LIEU": ["account", "asset_ticker", "trade_date", "quantity", "amount_usd"],
}


class EventForm(forms.ModelForm):
    asset_ticker = forms.CharField(max_length=32, required=False, label=LABELS["asset_ticker"])
    per_share_usd = forms.DecimalField(required=False, label=LABELS["per_share_usd"])
    ptax_manual = forms.DecimalField(
        required=False, max_digits=10, decimal_places=6, min_value=Decimal("0.01"),
        label="PTAX manual (opcional)",
        help_text="Informe se o BCB não responder. Consulte o fechamento PTAX no site do BC.",
    )
    ptax_reason = forms.CharField(
        max_length=255, required=False, strip=True,
        label="Motivo da PTAX manual",
        help_text="Ex.: API do BCB indisponível em 31/12/2026.",
    )
    income_receipt_date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"}),
        label="Data de recebimento do rendimento",
        help_text="Fato gerador do rendimento (auditoria-fiscal 10) — pode "
                  "diferir da data da operação. Vazio = recebido na data da operação.",
    )
    foreign_tax_payment_date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"}),
        label="Data de pagamento do imposto no exterior",
        help_text="Data documentada no extrato — pode diferir da data do rendimento.",
    )
    confirm_same_day = forms.BooleanField(
        required=False, label="Retenção na mesma data do rendimento",
        help_text="Marque somente se o extrato registrar retenção e rendimento na mesma data.",
    )
    date_evidence_source = forms.ChoiceField(
        required=False, choices=[("", "—")] + DATE_EVIDENCE_SOURCES,
        label="Fonte documental da data",
    )
    country_code = forms.CharField(max_length=2, initial="US", label="País")
    jurisdiction_level = forms.ChoiceField(choices=JURISDICTION_LEVELS, initial="FEDERAL", label="Jurisdição")
    tax_type = forms.ChoiceField(choices=TAX_TYPES, initial="WITHHOLDING_INCOME_TAX", label="Tipo de imposto")
    source_document_id = forms.CharField(max_length=128, required=False, label="ID do documento")
    source_reference = forms.CharField(max_length=255, required=False, label="Referência do documento")

    tax_usd = forms.DecimalField(
        required=False, min_value=Decimal("0.01"),
        label=LABELS["tax_usd"],
        help_text="Imposto retido no exterior — gera registro em ForeignTaxPayment "
                  "com país, jurisdição, tipo e data documentados.",
    )

    class Meta:
        model = FinancialEvent
        fields = ["event_type", "account", "trade_date", "income_receipt_date",
                  "quantity",
                  "price_usd", "fee_usd", "amount_usd",
                  "split_ratio_from", "split_ratio_to", "notes"]
        labels = {"event_type": LABELS["event_type"], "account": LABELS["account"],
                  "trade_date": LABELS["trade_date"], "quantity": LABELS["quantity"],
                  "price_usd": LABELS["price_usd"], "fee_usd": LABELS["fee_usd"],
                  "amount_usd": LABELS["amount_usd"],
                  "split_ratio_from": LABELS["split_ratio_from"],
                  "split_ratio_to": LABELS["split_ratio_to"],
                  "notes": LABELS["notes"]}
        widgets = {"trade_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ledger.models import BrokerAccount
        self.fields["account"].queryset = BrokerAccount.objects.filter(active=True)
        self.fields["account"].label_from_instance = lambda a: str(a)
        for f in self.fields.values():
            f.required = False
        if self.is_bound and self.data.get("event_type"):
            self.fields["event_type"].required = True

    def clean_asset_ticker(self):
        ticker = (self.cleaned_data.get("asset_ticker") or "").strip().upper()
        if not ticker:
            return None
        # RF-AST-003: sem auto-criação silenciosa — o ativo deve ser
        # cadastrado explicitamente com sua natureza jurídica.
        try:
            return Asset.objects.get(ticker=ticker, active=True)
        except Asset.DoesNotExist:
            raise forms.ValidationError(
                f"Ativo {ticker} não cadastrado. Cadastre-o explicitamente em "
                "ativos/novo/ antes de lançar eventos."
            )

    def clean(self):
        cleaned = super().clean()
        etype = cleaned.get("event_type")
        if not etype:
            self.add_error("event_type", "Selecione o tipo de evento.")
            return cleaned
        for name in REQUIRED_BY_TYPE.get(etype, []):
            if name == "asset_ticker":
                value = cleaned.get("asset_ticker")
            else:
                value = cleaned.get(name)
            if value in (None, ""):
                self.add_error(name, "Campo obrigatório para este tipo de evento.")
        if cleaned.get("ptax_manual") and not (cleaned.get("ptax_reason") or "").strip():
            self.add_error("ptax_reason", "Informe o motivo ao usar PTAX manual.")
        tax = cleaned.get("tax_usd")
        if tax and tax > 0:
            if not cleaned.get("foreign_tax_payment_date") and not cleaned.get("confirm_same_day"):
                self.add_error(
                    "foreign_tax_payment_date",
                    "Informe a data de pagamento do imposto no exterior ou confirme "
                    "que coincide com a data do rendimento.",
                )
            if not cleaned.get("date_evidence_source") or cleaned.get("date_evidence_source") == "UNKNOWN":
                self.add_error(
                    "date_evidence_source",
                    "Informe a fonte documental da data do imposto no exterior.",
                )
        return cleaned


class AssetForm(forms.ModelForm):
    """Cadastro explícito de ativo com natureza jurídica legal (RF-AST-003/006)."""

    class Meta:
        model = Asset
        fields = ["ticker", "description", "asset_type", "country_code",
                  "is_controlled_entity", "ownership_share_pct"]
        labels = {
            "ticker": "Ticker",
            "description": "Descrição",
            "asset_type": "Natureza jurídica",
            "country_code": "País",
            "is_controlled_entity": "Entidade controlada (offshore)",
            "ownership_share_pct": "Participação do contribuinte (%)",
        }
        widgets = {"description": forms.TextInput(attrs={"size": 40})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ownership_share_pct"].required = False
        self.fields["is_controlled_entity"].required = False

    def clean_ticker(self):
        return (self.cleaned_data.get("ticker") or "").strip().upper()

    def clean_ownership_share_pct(self):
        pct = self.cleaned_data.get("ownership_share_pct")
        if pct is not None and not (Decimal(0) <= pct <= Decimal(100)):
            raise forms.ValidationError("Participação deve estar entre 0 e 100.")
        return pct
