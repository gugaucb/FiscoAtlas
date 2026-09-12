from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import generic

from ledger.cash import CashLedgerService
from ledger.forms import AssetForm, EventForm, ForeignTaxPaymentForm
from ledger.models import Asset, FinancialEvent, ForeignTaxPayment
from ledger.position import PositionService
from ledger.service import EventService


class AssetCreateView(generic.CreateView):
    """Cadastro explícito de ativo (RF-AST-003): natureza jurídica obrigatória,
    sem inferência silenciosa de tipo."""
    form_class = AssetForm
    template_name = "ledger/asset_form.html"
    success_url = reverse_lazy("event-create")

    def form_valid(self, form):
        messages.success(self.request, "Ativo cadastrado.")
        return super().form_valid(form)


class EventListView(generic.ListView):
    model = FinancialEvent
    template_name = "ledger/event_list.html"
    context_object_name = "events"
    queryset = FinancialEvent.objects.filter(active=True).prefetch_related("foreign_tax_payments").order_by("-trade_date", "-id")


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
                    "price_usd", "fee_usd", "amount_usd", "notes")}
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


class ForeignTaxPaymentEditView(generic.UpdateView):
    """Correção documental do imposto pago no exterior, com trilha de auditoria."""
    form_class = ForeignTaxPaymentForm
    template_name = "ledger/foreign_tax_edit.html"
    success_url = reverse_lazy("event-list")
    queryset = ForeignTaxPayment.objects.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["audits"] = self.object.audits.order_by("-changed_at")
        return ctx

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Imposto no exterior atualizado; alteração registrada na trilha de auditoria.")
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


class StatementImportView(generic.View):
    """RF-IMP-001..004: upload de extrato CSV com preview (GET ?csv=…)
    e importação idempotente por hash (CT-030)."""

    template_name = "ledger/import_form.html"

    def get(self, request, account_id):
        from ledger.models import BrokerAccount

        conta = BrokerAccount.objects.get(pk=account_id)
        from ledger.models import ImportIssue

        ctx = {
            "account": conta, "preview": None, "csv_text": "",
            "pendencias_abertas": ImportIssue.objects.filter(
                batch__account=conta, status=ImportIssue.STATUS_PENDING,
            ).count(),
        }
        csv_text = request.GET.get("csv", "")
        if csv_text:
            from ledger.importers.schwab import SchwabStatementImporter

            importer = SchwabStatementImporter(conta)
            preview = importer.preview(csv_text)
            ctx["preview"] = preview
            ctx["pendencias"] = [r for r in preview if r.get("status") != "OK"]
            ctx["n_suportadas"] = sum(1 for r in preview if r.get("status") == "OK")
            ctx["csv_text"] = csv_text
        return render(request, self.template_name, ctx)

    def post(self, request, account_id):
        from django.core.exceptions import ValidationError
        from django.db import transaction
        from django.shortcuts import get_object_or_404

        from ledger.importers.base import StatementImportError
        from ledger.importers.schwab import SchwabStatementImporter
        from ledger.models import BrokerAccount

        conta = get_object_or_404(BrokerAccount, pk=account_id)
        arquivo = request.FILES.get("arquivo")
        if arquivo is None:
            messages.error(request, "Selecione o arquivo CSV do extrato.")
            return redirect("import-statement", account_id=account_id)
        text = arquivo.read().decode("utf-8-sig", errors="replace")
        acknowledge = bool(request.POST.get("reconhecer_pendencias"))
        try:
            with transaction.atomic():
                batch = SchwabStatementImporter(conta).import_csv(
                    text, acknowledge_pending=acknowledge
                )
        except (StatementImportError, ValidationError, ValueError) as e:
            transaction.set_rollback(True)
            messages.error(request, f"Falha na importação: {e}")
            return redirect("import-statement", account_id=account_id)
        if batch.events_created == 0:
            messages.info(request, "Arquivo já importado anteriormente — nenhum evento criado.")
        else:
            msg = f"Extrato importado: {batch.events_created} evento(s) criado(s)."
            if batch.rows_unsupported:
                msg += f" {batch.rows_unsupported} linha(s) com ação não suportada registradas como pendência — resolva-as antes do fechamento anual."
                messages.warning(request, msg)
            else:
                messages.success(request, msg)
        return redirect("import-statement", account_id=account_id)
