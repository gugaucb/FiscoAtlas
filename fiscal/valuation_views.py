"""Ticket 07 (auditoria-fiscal): valor de mercado do ativo na data-base.

Entrada mínima de AssetValuation — a CBE usa SOMENTE valor confirmado
na data-base; sem valor, o item fica UNDETERMINED (sem custo médio)."""
from django.contrib import messages
from django.urls import reverse_lazy
from django.views import generic

from fiscal.models import AssetValuation
from fiscal.valuation_forms import AssetValuationForm


class AssetValuationView(generic.CreateView):
    form_class = AssetValuationForm
    template_name = "fiscal/valuation.html"
    success_url = reverse_lazy("asset-valuation")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["valuations"] = AssetValuation.objects.select_related(
            "account", "asset").order_by("-reference_date", "account__broker_name")
        ctx["form"] = self.get_form()
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Valor na data-base registrado.")
        return super().form_valid(form)