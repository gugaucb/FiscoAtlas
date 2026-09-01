import django.forms as forms
from ledger.models import Asset, OpeningPosition


class OpeningPositionForm(forms.ModelForm):
    asset_ticker = forms.CharField(max_length=32, required=True, label="Ativo (ticker)")

    class Meta:
        model = OpeningPosition
        fields = ["account", "reference_date", "quantity", "total_cost_brl", "notes"]
        labels = {
            "account": "Conta",
            "reference_date": "Data de referência",
            "quantity": "Quantidade",
            "total_cost_brl": "Custo fiscal total (BRL)",
            "notes": "Observações",
        }
        widgets = {"reference_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ledger.models import BrokerAccount
        self.fields["account"].required = False
        self.fields["account"].queryset = BrokerAccount.objects.filter(active=True)
        self.fields["notes"].required = False

    def clean_asset_ticker(self):
        ticker = (self.cleaned_data.get("asset_ticker") or "").strip().upper()
        asset, _ = Asset.objects.get_or_create(
            ticker=ticker,
            defaults={"description": ticker, "asset_type": "STOCK", "country_code": "US"},
        )
        return asset

    def save(self, commit=True):
        self.instance.asset = self.cleaned_data["asset_ticker"]
        return super().save(commit)
