from datetime import date
from decimal import Decimal

from django import forms
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views import generic

from fiscal.engine import TaxEngine
from fiscal.memoria import build_memoria, render_memoria_pdf
from fiscal.models import AnnualAssessment
from fiscal.pdf import render_pdf
from fiscal.report import ReportService
from fx.service import PtaxService


class FriendlyErrorMixin:
    """Captura erros de negócio (ex.: PTAX de data futura) e mostra
    mensagem amigável em vez de stack de erro."""

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except ValueError as e:
            return render(request, "fiscal/erro.html", {"message": str(e)}, status=200)


class AssessmentView(FriendlyErrorMixin, generic.TemplateView):
    template_name = "fiscal/assessment.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        year = self.kwargs["year"]
        ctx["year"] = year
        ctx["result"] = TaxEngine(year).compute()
        ctx["snapshot"] = AnnualAssessment.objects.filter(year=year).first()
        return ctx


class CloseYearView(FriendlyErrorMixin, generic.View):
    """Salva o snapshot de fechamento do ano (idempotente) e volta para a apuração."""

    def post(self, request, year):
        from django.contrib import messages
        from django.core.exceptions import ValidationError
        from django.db import transaction

        from fiscal.reconciliation import AnnualReconciliationService
        from fiscal.validator import AnnualClosingValidator

        try:
            with transaction.atomic():
                # Auditoria-fiscal 12: primeiro a reconciliação (dados de
                # entrada completos e conciliados), depois as regras fiscais.
                AnnualReconciliationService(year).run_or_raise()
                AnnualClosingValidator(year).validate_or_raise()
                result = TaxEngine(year).compute()
                snapshot = TaxEngine.save_snapshot(year)
                snapshot.confirmed = True
                snapshot.save(update_fields=["confirmed"])
        except ValidationError as e:
            for msg in e.messages:
                messages.error(request, str(msg))
            return redirect("assessment", year=year)
        messages.success(
            request,
            f"Ano {year} fechado. Imposto devido: R$ {result['tax_due_brl']} — "
            f"Prejuízo a compensar: R$ {result['loss_carryforward_brl']}",
        )
        return redirect("assessment", year=year)


class FechamentoPtaxForm(forms.Form):
    rate = forms.DecimalField(
        label="PTAX venda 31/12", max_digits=10, decimal_places=6, min_value=Decimal("0.01"),
    )
    motivo = forms.CharField(label="Motivo", max_length=255, strip=True)


class ReportView(FriendlyErrorMixin, generic.TemplateView):
    template_name = "fiscal/report.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        year = self.kwargs["year"]
        ctx["year"] = year
        try:
            ctx["report"] = ReportService(year).build()
        except ValueError as e:
            if "PTAX" not in str(e):
                raise
            # 31/12 sem cotação (ex.: data futura): oferece registro manual inline
            ctx["report"] = None
            ctx["ptax_form"] = FechamentoPtaxForm()
            return ctx
        if self.request.GET.get("ptax") == "editar":
            vigente = ctx["report"]["ptax_yearend"]
            ctx["ptax_form"] = FechamentoPtaxForm(
                initial={"rate": vigente["rate"], "motivo": ""}
            )
        return ctx


class FechamentoPtaxView(generic.View):
    """Registra PTAX de fechamento 31/12 manual (override) e volta ao relatório."""

    def post(self, request, year):
        form = FechamentoPtaxForm(request.POST)
        if not form.is_valid():
            return render(
                request, "fiscal/report.html",
                {"report": None, "year": year, "ptax_form": form}, status=200,
            )
        PtaxService().override(date(year, 12, 31), form.cleaned_data["rate"], form.cleaned_data["motivo"])
        return redirect("report", year=year)


class ReportPdfView(FriendlyErrorMixin, generic.View):
    def get(self, request, year):
        pdf = render_pdf(ReportService(year).build())
        resp = HttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="relatorio-dirpf-{year}.pdf"'
        return resp


class MemoriaPdfView(FriendlyErrorMixin, generic.View):
    def get(self, request, year):
        pdf = render_memoria_pdf(build_memoria(year))
        resp = HttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="MEMORIA_CALCULO_{year}.pdf"'
        return resp
