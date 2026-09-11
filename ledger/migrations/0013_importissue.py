# Auditoria-fiscal ticket 01: ImportIssue (pendência explícita de importação)
# + contadores de conciliação em ImportBatch (linhas do arquivo = importadas
# + pendências + ignoradas confirmadas).
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0012_importbatch'),
    ]

    operations = [
        migrations.AddField(
            model_name='importbatch',
            name='rows_source',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='importbatch',
            name='rows_imported',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='importbatch',
            name='rows_unsupported',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='importbatch',
            name='rows_ignored_confirmed',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name='ImportIssue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('line_number', models.PositiveIntegerField()),
                ('raw_action', models.CharField(blank=True, max_length=128)),
                ('raw_data', models.JSONField(default=dict)),
                ('severity', models.CharField(default='BLOCKING', max_length=16)),
                ('reason', models.CharField(blank=True, max_length=255)),
                ('status', models.CharField(choices=[('PENDING', 'Pendente'), ('RESOLVED_IMPORTED', 'Resolvido — lançado manualmente'), ('RESOLVED_IGNORED', 'Resolvido — ignorado com justificativa')], default='PENDING', max_length=32)),
                ('resolution', models.CharField(blank=True, max_length=255)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='issues', to='ledger.importbatch')),
            ],
            options={
                'ordering': ['batch', 'line_number'],
            },
        ),
    ]
