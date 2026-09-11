"""Ticket 07 (auditoria-fiscal): formulário de valor na data-base (CBE v2)."""
from django import forms

from fiscal.models import AssetValuation


class AssetValuationForm(forms.ModelForm):
    class Meta:
        model = AssetValuation
        fields = ["account", "asset", "reference_date", "value_usd",
                  "valuation_method", "confirmed", "source_document_id", "source_reference"]
        labels = {
            "account": "Conta",
            "asset": "Ativo",
            "reference_date": "Data-base",
            "value_usd": "Valor de mercado (USD)",
            "valuation_method": "Método de valuation",
            "confirmed": "Confirmado pelo contribuinte",
            "source_document_id": "ID do documento",
            "source_reference": "Referência do documento",
        }
        widgets = {
            "reference_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ledger.models import Asset, BrokerAccount
        self.fields["account"].queryset = BrokerAccount.objects.filter(active=True)
        self.fields["asset"].queryset = Asset.objects.filter(active=True)
        self.fields["confirmed"].required = False
        self.fields["source_document_id"].required = False
        self.fields["source_reference"].required = False