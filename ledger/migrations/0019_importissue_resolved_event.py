from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ledger", "0018_foreigntaxpayment_recoverability_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="importissue",
            name="resolved_event",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=models.deletion.PROTECT,
                related_name="resolved_import_issues",
                to="ledger.financialevent",
            ),
        ),
    ]