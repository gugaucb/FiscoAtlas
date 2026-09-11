"""Auditoria-fiscal 12: formulário do saldo documental da data-base."""
from django import forms

from ledger.models import DocumentedBalance


class DocumentedBalanceForm(forms.ModelForm):
    positions_text = forms.CharField(
        required=False, strip=True, widget=forms.Textarea(attrs={"rows": 4}),
        label="Posições documentadas",
        help_text="Uma por linha: TICKER, QUANTIDADE (ex.: AAPL, 150). "
                  "Deixe vazio se não há posições em custódia.",
    )

    class Meta:
        model = DocumentedBalance
        fields = ["account", "reference_date", "cash_usd", "confirmed",
                  "source_document_id", "source_reference"]
        labels = {
            "account": "Conta",
            "reference_date": "Data-base",
            "cash_usd": "Saldo de caixa documentado (USD)",
            "confirmed": "Confirmado pelo contribuinte (confronta extrato)",
            "source_document_id": "ID do documento",
            "source_reference": "Referência do documento",
        }
        widgets = {"reference_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ledger.models import BrokerAccount
        self.fields["account"].queryset = BrokerAccount.objects.filter(active=True)
        self.fields["confirmed"].required = False
        self.fields["source_document_id"].required = False
        self.fields["source_reference"].required = False

    def clean_positions_text(self):
        texto = self.cleaned_data.get("positions_text") or ""
        posicoes = []
        for linha in texto.strip().splitlines():
            if not linha.strip():
                continue
            partes = [p.strip() for p in linha.split(",")]
            if len(partes) != 2 or not partes[1]:
                raise forms.ValidationError(
                    f"Linha inválida: '{linha}'. Use TICKER, QUANTIDADE."
                )
            posicoes.append({"ticker": partes[0].upper(), "quantity": partes[1]})
        return posicoes

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("confirmed") is False:
            self.add_error("confirmed", "Confirme o confronto com o extrato — saldo não confirmado não reconcilia.")
        return cleaned

    def save(self, commit=True):
        self.instance.positions = self.cleaned_data.get("positions_text") or []
        return super().save(commit=commit)