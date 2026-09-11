# Auditoria-fiscal ticket 04: ForeignTaxPayment como fonte única.
# 1) Migra dados: eventos legados com tax_usd > 0 recebem um ForeignTaxPayment
#    com fatos marcados para revisão (jurisdição/tipo/evidência UNKNOWN →
#    crédito não elegível até classificação — sem regra fiscal silenciosa).
# 2) Remove o campo duplicado FinancialEvent.tax_usd.
from django.db import migrations


def migrar_tax_para_foreign_tax_payment(apps, schema_editor):
    FinancialEvent = apps.get_model("ledger", "FinancialEvent")
    ForeignTaxPayment = apps.get_model("ledger", "ForeignTaxPayment")
    for ev in FinancialEvent.objects.filter(tax_usd__gt=0).iterator():
        if ev.foreign_tax_payments.exists():
            continue  # já tem pagamento registrado — não duplica
        ForeignTaxPayment.objects.create(
            financial_event=ev,
            tax_usd=ev.tax_usd,
            foreign_tax_payment_date=ev.trade_date,
            # fatos desconhecidos exigem classificação posterior; país "US"
            # é o contexto do sistema, mas jurisdição/tipo UNKNOWN impedem
            # crédito automático até o usuário classificar.
            country_code="US",
            jurisdiction_level="UNKNOWN",
            tax_type="UNKNOWN",
            capture_method="SYSTEM",
            date_evidence_source="UNKNOWN",
            source_reference="migração do campo legado tax_usd (auditoria-fiscal 04)",
        )


def desfazer(apps, schema_editor):
    # Não devolve o valor ao campo removido: dados já consolidados na nova fonte.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0014_openingposition_uniq_account_asset_date'),
    ]

    operations = [
        migrations.RunPython(migrar_tax_para_foreign_tax_payment, desfazer),
        migrations.RemoveField(
            model_name='financialevent',
            name='tax_usd',
        ),
    ]
