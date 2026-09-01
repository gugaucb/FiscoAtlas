from django.core.exceptions import ValidationError
from django.db import models


class Profile(models.Model):
    """Beneficiário único (single-user, ADR-0002)."""
    name = models.CharField(max_length=255)
    cpf = models.CharField(max_length=14)

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
    tax_year = models.PositiveIntegerField()
    rule_version = models.CharField(max_length=64)
    brackets = models.JSONField()  # [{"limit_brl": "6000.00"|None, "rate": "0.15"}]
    foreign_tax_credit_enabled = models.BooleanField(default=True)
    loss_carryforward_enabled = models.BooleanField(default=True)
    fx_cash_policy = models.JSONField(default=dict)  # política de caixa não remunerado
    quote_type = models.CharField(max_length=10, default="VENDA")
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
