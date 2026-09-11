# Auditoria-fiscal 08: regras de arrecadação do DARF versionadas por
# exercício (não mais constantes hardcoded no código).
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fiscal', '0009_dirpfschema'),
    ]

    operations = [
        migrations.CreateModel(
            name='FilingRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filing_year', models.PositiveIntegerField(unique=True)),
                ('rule_version', models.CharField(max_length=64)),
                ('due_date', models.DateField()),
                ('darf_code', models.CharField(max_length=4)),
                ('minimum_darf', models.DecimalField(decimal_places=2, default=10, max_digits=20)),
                ('minimum_installment', models.DecimalField(decimal_places=2, max_digits=20)),
                ('minimum_tax_for_installment', models.DecimalField(decimal_places=2, max_digits=20)),
                ('maximum_installments', models.PositiveIntegerField()),
                ('is_homologated', models.BooleanField(default=False)),
                ('legal_basis', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
