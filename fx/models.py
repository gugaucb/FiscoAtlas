from django.db import models


class PtaxRate(models.Model):
    QUOTE_TYPES = [("VENDA", "PTAX venda"), ("COMPRA", "PTAX compra")]

    requested_date = models.DateField()
    effective_date = models.DateField()
    quote_type = models.CharField(max_length=10, choices=QUOTE_TYPES, default="VENDA")
    rate = models.DecimalField(max_digits=12, decimal_places=8)
    source = models.CharField(max_length=64, default="BCB-OLINDA")
    fetched_at = models.DateTimeField(auto_now=True)
    manually_overridden = models.BooleanField(default=False)
    override_reason = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["effective_date", "quote_type"],
                condition=models.Q(manually_overridden=False),
                name="uniq_ptax_effective_quote",
            )
        ]

    def __str__(self):
        return f"PTAX {self.quote_type} {self.effective_date} = {self.rate}"
