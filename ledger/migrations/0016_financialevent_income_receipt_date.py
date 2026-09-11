from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ledger", "0015_remove_financialevent_tax_usd"),
    ]

    operations = [
        migrations.AddField(
            model_name="financialevent",
            name="income_receipt_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]