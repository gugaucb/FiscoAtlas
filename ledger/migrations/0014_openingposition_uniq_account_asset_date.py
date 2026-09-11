# Auditoria-fiscal ticket 03: abertura estritamente por conta.
# Constraint de unicidade (account, asset, reference_date). O campo account
# permanece nullable no schema para aberturas legadas: a leitura fiscal é
# sempre por conta (ledger/position.py) e o formulário exige conta.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0013_importissue'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='openingposition',
            constraint=models.UniqueConstraint(fields=('account', 'asset', 'reference_date'), name='uniq_opening_account_asset_date'),
        ),
    ]
