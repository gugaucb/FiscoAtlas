import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fiscal", "0010_filingrule"),
        ("ledger", "0016_financialevent_income_receipt_date"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssetValuation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference_date", models.DateField()),
                ("value_usd", models.DecimalField(decimal_places=2, max_digits=20)),
                ("valuation_method", models.CharField(choices=[("MARKET_CLOSE", "Preço de fechamento na data-base"), ("BROKER_STATEMENT", "Extrato da corretora na data-base"), ("USER_PROVIDED", "Valor informado pelo contribuinte")], max_length=32)),
                ("confirmed", models.BooleanField(default=False)),
                ("source_document_id", models.CharField(blank=True, max_length=128)),
                ("source_reference", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="asset_valuations", to="ledger.brokeraccount")),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="valuations", to="ledger.asset")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("account", "asset", "reference_date"), name="uniq_valuation_account_asset_date"),
                ],
            },
        ),
    ]