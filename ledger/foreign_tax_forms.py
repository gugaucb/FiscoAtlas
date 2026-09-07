from decimal import Decimal

from django import forms
from django.utils import timezone

from ledger.models import ForeignTaxPayment, ForeignTaxPaymentAudit

EDITABLE_FIELDS = (
    "foreign_tax_payment_date", "jurisdiction_level", "tax_type",
    "date_evidence_source", "source_document_id", "source_reference",
)


class ForeignTaxPaymentForm(forms.ModelForm):
    reason = forms.CharField(
        max_length=255, strip=True, label="Motivo da alteração",
        help_text="Obrigatório: a alteração fica registrada na trilha de auditoria.",
    )
    ptax_compra_manual = forms.DecimalField(
        required=False, max_digits=10, decimal_places=6, min_value=Decimal("0.01"),
        label="PTAX COMPRA manual (opcional)",
        help_text="Informe se o BCB não responder. Consulte o fechamento PTAX no site do BC.",
    )

    class Meta:
        model = ForeignTaxPayment
        fields = EDITABLE_FIELDS
        widgets = {"foreign_tax_payment_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._old_values = {
            field: getattr(self.instance, field) for field in EDITABLE_FIELDS
        }

    def clean_reason(self):
        motivo = (self.cleaned_data.get("reason") or "").strip()
        if not motivo:
            raise forms.ValidationError("Informe o motivo da alteração.")
        return motivo

    def save(self):
        pagamento = super().save(commit=False)
        changes = [
            {"field": field, "old": str(old), "new": str(getattr(pagamento, field))}
            for field, old in self._old_values.items()
            if old != getattr(pagamento, field)
        ]
        pagamento.save()
        manual = self.cleaned_data.get("ptax_compra_manual")
        if manual is not None:
            from fx.service import PtaxService
            anterior = PtaxService().get_rate(
                pagamento.foreign_tax_payment_date, quote_type="COMPRA"
            ).rate
            PtaxService().override(
                pagamento.foreign_tax_payment_date, manual,
                self.cleaned_data["reason"], quote_type="COMPRA",
            )
            if anterior != manual:
                changes.append({
                    "field": "ptax_compra", "old": str(anterior), "new": str(manual),
                })
        if changes:
            ForeignTaxPaymentAudit.objects.create(
                payment=pagamento, changes=changes,
                reason=self.cleaned_data["reason"], changed_at=timezone.now(),
            )
        return pagamento
