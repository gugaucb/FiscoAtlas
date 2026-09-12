from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ledger", "0017_foreigntaxstate_documentedbalance"),
    ]

    operations = [
        migrations.AddField(
            model_name="foreigntaxpayment",
            name="recoverability_status",
            field=models.CharField(
                choices=[
                    ("NON_RECOVERABLE", "Não recuperável (caráter definitivo)"),
                    ("RECOVERABLE", "Recuperável no exterior (restituição/reembolso/compensação)"),
                    ("UNKNOWN", "Desconhecida — classifique antes de fechar o ano"),
                ],
                default="UNKNOWN",
                max_length=20,
            ),
        ),
    ]