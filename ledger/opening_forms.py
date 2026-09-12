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
        # Auditoria-fiscal 03: abertura é por conta — obrigatória no cadastro
        self.fields["account"].required = True
        self.fields["account"].queryset = BrokerAccount.objects.filter(active=True)
        self.fields["notes"].required = False

    def clean_asset_ticker(self):
        """P0 do auditor: fim do get_or_create com asset_type='STOCK' — valor
        fora da taxonomia legal (RF-AST-003/006) e criação silenciosa de ativo
        sem classificação. Só ativo previamente cadastrado e ativo."""
        ticker = (self.cleaned_data.get("asset_ticker") or "").strip().upper()
        asset = Asset.objects.filter(ticker=ticker, active=True).first()
        if asset is None:
            raise forms.ValidationError(
                f"Ativo {ticker} não cadastrado (ou inativo). Cadastre e "
                "classifique a natureza jurídica em /ativos/novo/ antes de "
                "lançar a posição de abertura — sem criação automática."
            )
        return asset

    def save(self, commit=True):
        self.instance.asset = self.cleaned_data["asset_ticker"]
        return super().save(commit)
