import django.forms as forms
from ledger.models import BrokerAccount


class BrokerAccountForm(forms.ModelForm):
    class Meta:
        model = BrokerAccount
        fields = ["name", "broker_name", "account_number", "account_type", "is_interest_bearing"]
        labels = {
            "name": "Nome do caixa (apelido)",
            "broker_name": "Corretora",
            "account_number": "Número da conta",
            "account_type": "Tipo",
            "is_interest_bearing": "Conta remunerada",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].required = True
        self.fields["is_interest_bearing"].required = False
