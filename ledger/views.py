from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import generic

from ledger.cash import CashLedgerService
from ledger.forms import EventForm
from ledger.models import Asset, FinancialEvent
from ledger.position import PositionService
from ledger.service import EventService


class EventListView(generic.ListView):
    model = FinancialEvent
    template_name = "ledger/event_list.html"
    context_object_name = "events"
    queryset = FinancialEvent.objects.filter(active=True).order_by("-trade_date", "-id")


class EventCreateView(generic.CreateView):
    form_class = EventForm
    template_name = "ledger/event_form.html"
    success_url = reverse_lazy("event-list")

    def form_valid(self, form):
        data = form.cleaned_data
        data["asset"] = data.pop("asset_ticker", None)
        try:
            EventService().record(data)
        except ValueError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        messages.success(self.request, "Evento registrado.")
        return redirect(self.success_url)


class EventDeactivateView(generic.View):
    """Soft delete: desativa o evento; ele deixa de ser contabilizado."""

    def post(self, request, pk):
        ev = FinancialEvent.objects.filter(pk=pk, active=True).first()
        if ev:
            ev.active = False
            ev.save(update_fields=["active"])
            messages.success(request, "Evento desativado; deixou de ser contabilizado.")
        return redirect("event-list")


class EventCorrectView(generic.UpdateView):
    form_class = EventForm
    template_name = "ledger/event_form.html"
    success_url = reverse_lazy("event-list")
    queryset = FinancialEvent.objects.filter(active=True)

    def get_initial(self):
        ev = self.get_object()
        initial = {f: getattr(ev, f) for f in
                   ("event_type", "account", "trade_date", "quantity",
                    "price_usd", "fee_usd", "tax_usd", "amount_usd", "notes")}
        initial["asset_ticker"] = ev.asset.ticker if ev.asset else None
        return initial

    def form_valid(self, form):
        data = form.cleaned_data
        data["asset"] = data.pop("asset_ticker", None)
        data["corrects"] = self.get_object()
        try:
            EventService().record(data)
        except ValueError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        messages.success(self.request, "Correção registrada; evento original desativado.")
        return redirect(self.success_url)


class PositionsView(generic.TemplateView):
    template_name = "ledger/positions.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        rows = []
        accounts = FinancialEvent.objects.filter(active=True).values_list("account", flat=True).distinct()
        for asset in Asset.objects.filter(events__active=True).distinct():
            for account_id in set(accounts):
                pos = PositionService().position(account_id, asset)
                if pos["quantity"]:
                    rows.append({"asset": asset, **pos})
        ctx["rows"] = rows
        return ctx


class CashView(generic.TemplateView):
    template_name = "ledger/cash.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["accounts"] = []
        from ledger.models import BrokerAccount
        for acct in BrokerAccount.objects.all():
            ctx["accounts"].append({
                "account": acct,
                "balance": CashLedgerService().balance(acct),
                "history": CashLedgerService().history(acct),
            })
        return ctx
