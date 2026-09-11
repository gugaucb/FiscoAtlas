"""Auditoria-fiscal 12: saldos documentais da corretora na data-base."""
from django.contrib import messages
from django.urls import reverse_lazy
from django.views import generic

from ledger.models import DocumentedBalance
from fiscal.reconciliation_forms import DocumentedBalanceForm


class DocumentedBalanceView(generic.CreateView):
    form_class = DocumentedBalanceForm
    template_name = "fiscal/documented_balance.html"
    success_url = reverse_lazy("documented-balance")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["balances"] = DocumentedBalance.objects.select_related(
            "account").order_by("-reference_date", "account__broker_name")
        ctx["form"] = self.get_form()
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Saldo documental registrado.")
        return super().form_valid(form)