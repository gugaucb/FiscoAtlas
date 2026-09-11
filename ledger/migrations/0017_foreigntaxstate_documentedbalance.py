import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ledger", "0016_financialevent_income_receipt_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="financialevent",
            name="foreign_tax_state",
            field=models.CharField(
                choices=[
                    ("UNDECLARED", "Não declarado"),
                    ("NO_WITHHOLDING", "Sem retenção no exterior (declarado pelo contribuinte)"),
                    ("RECORDED", "Registrado em ForeignTaxPayment"),
                    ("REVIEW_PENDING", "Pendente de revisão documental"),
                ],
                default="UNDECLARED", max_length=16,
            ),
        ),
        migrations.CreateModel(
            name="DocumentedBalance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference_date", models.DateField()),
                ("cash_usd", models.DecimalField(decimal_places=2, max_digits=20)),
                ("positions", models.JSONField(default=list)),
                ("confirmed", models.BooleanField(default=False)),
                ("source_document_id", models.CharField(blank=True, max_length=128)),
                ("source_reference", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="documented_balances", to="ledger.brokeraccount")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("account", "reference_date"), name="uniq_documented_balance"),
                ],
            },
        ),
    ]