from django.core.exceptions import ValidationError
from django.db import models


RESIDENCY_STATUSES = [
    ("BRAZIL_RESIDENT", "Residente fiscal pleno no Brasil"),
    ("NON_RESIDENT", "Não residente"),
    ("PART_YEAR_RESIDENT", "Residente por parte do ano-calendário"),
    ("UNKNOWN", "Desconhecida"),
]


class Profile(models.Model):
    """Beneficiário único (single-user, ADR-0002)."""
    name = models.CharField(max_length=255)
    cpf = models.CharField(max_length=14)
    # RF-PER-001: condição de residência fiscal — pré-condição de apuração
    # (Lei 14.754/2023 aplica-se a residentes; RF-VAL-001)
    tax_residency_status = models.CharField(max_length=20, choices=RESIDENCY_STATUSES, default="UNKNOWN")
    residency_start_date = models.DateField(null=True, blank=True)
    residency_end_date = models.DateField(null=True, blank=True)
    has_dsdp = models.BooleanField(default=False)
    # RF-CBE-005: declaração formal de que não há outros bens no exterior
    # fora da plataforma (transforma CBE_UNDETERMINED em CBE_NOT_REQUIRED)
    external_assets_declared_complete = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if Profile.objects.exclude(pk=self.pk).exists():
            raise ValidationError("Só pode existir um Profile (single-user).")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TaxRuleQuerySet(models.QuerySet):
    def for_year(self, year: int) -> "TaxRule":
        rule = (
            self.filter(tax_year=year, confirmed=True)
            .order_by("-rule_version")
            .first()
        )
        if rule is None:
            raise ValueError(f"Sem TaxRule confirmada para o ano {year}")
        return rule


class TaxRule(models.Model):
    DATE_RULES = [
        ("ACQUISITION_DATE", "Data da aquisição"),
        ("DISPOSAL_DATE", "Data da alienação"),
        ("INCOME_RECEIPT_DATE", "Data do recebimento do rendimento"),
        ("FOREIGN_TAX_PAYMENT_DATE", "Data do pagamento do imposto no exterior"),
        ("REFERENCE_DATE", "Data de referência informada"),
    ]

    tax_year = models.PositiveIntegerField()
    rule_version = models.CharField(max_length=64)
    brackets = models.JSONField()  # [{"limit_brl": "6000.00"|None, "rate": "0.15"}]
    foreign_tax_credit_enabled = models.BooleanField(default=True)
    loss_carryforward_enabled = models.BooleanField(default=True)
    fx_cash_policy = models.JSONField(default=dict)  # política de caixa não remunerado
    quote_type = models.CharField(max_length=10, default="VENDA")
    date_rule = models.CharField(max_length=32, choices=DATE_RULES, default="INCOME_RECEIPT_DATE")
    confirmed = models.BooleanField(default=False)
    notes = models.CharField(max_length=500, blank=True)
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)

    objects = TaxRuleQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tax_year", "rule_version"], name="uniq_taxrule_year_version"
            )
        ]


class AnnualAssessment(models.Model):
    year = models.PositiveIntegerField(unique=True)
    rule_version = models.CharField(max_length=64)
    income_brl = models.DecimalField(max_digits=20, decimal_places=8)
    loss_brl = models.DecimalField(max_digits=20, decimal_places=8)
    taxable_brl = models.DecimalField(max_digits=20, decimal_places=8)
    tax_brl = models.DecimalField(max_digits=20, decimal_places=8)
    withholding_credit_brl = models.DecimalField(max_digits=20, decimal_places=8)
    tax_due_brl = models.DecimalField(max_digits=20, decimal_places=8)
    loss_carryforward_brl = models.DecimalField(max_digits=20, decimal_places=8)
    detail = models.JSONField(default=list)
    computed_at = models.DateTimeField(auto_now=True)
    confirmed = models.BooleanField(default=False)


class LossRecord(models.Model):
    """RF-LOS-006: prejuízo rastreável até o evento de alienação e o ano de
    origem. O saldo remanescente é atualizado a cada compensação (FIFO)."""

    origin_year = models.PositiveIntegerField()
    source_event = models.ForeignKey(
        "ledger.FinancialEvent", on_delete=models.PROTECT,
        null=True, blank=True, related_name="loss_records",
    )
    description = models.CharField(max_length=255, blank=True)
    amount_brl = models.DecimalField(max_digits=20, decimal_places=2)
    remaining_brl = models.DecimalField(max_digits=20, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Perda {self.origin_year}: R$ {self.remaining_brl} a compensar"


class LossCompensation(models.Model):
    """RF-LOS-007: trilha auditável — quanto de cada perda foi compensada
    em cada ano (FIFO; reexecução do fechamento é idempotente)."""

    record = models.ForeignKey(LossRecord, on_delete=models.PROTECT, related_name="compensations")
    year = models.PositiveIntegerField()
    amount_brl = models.DecimalField(max_digits=20, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["record", "year"], name="uniq_loss_comp_year")
        ]
