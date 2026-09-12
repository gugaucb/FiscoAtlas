from datetime import date
from decimal import Decimal

from django import forms
from django.http import HttpResponse
from django.db import transaction
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

        # Ticket 29 (P0 do auditor): ano confirmado não pode ser fechado
        # novamente — proteção no BACKEND (não confiar na UI). Reabrir
        # explicitamente é o único caminho para novo fechamento.
        if AnnualAssessment.objects.filter(year=year, confirmed=True).exists():
            messages.error(
                request,
                f"O ano-calendário {year} já está fechado. Reabra o ano "
                "antes de realizar novo fechamento.",
            )
            return redirect("assessment", year=year)

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


class ReopenYearView(FriendlyErrorMixin, generic.View):
    """P0 do auditor (23): reabertura formal do ano pela aplicação — nada
    de SQL manual. Bloqueada se algum ano POSTERIOR está fechado (reabrir
    um ano anterior desfaria consumos de prejuízo em cascata): reabra do
    mais recente para o mais antigo. Apaga o snapshot do ano; a trilha
    fica na mensagem e o relatório dos anos seguintes volta a exibir o
    aviso de "ano anterior não fechado"."""

    def post(self, request, year):
        from django.contrib import messages

        from fiscal.models import AnnualAssessment

        if AnnualAssessment.objects.filter(year__gt=year, confirmed=True).exists():
            messages.error(
                request,
                f"Não é possível reabrir {year}: existem anos posteriores "
                "fechados. Reabra do mais recente para o mais antigo.",
            )
            return redirect("assessment", year=year)
        if (request.POST.get("confirmar") or "") != str(year):
            messages.error(request, "Confirmação da reabertura ausente ou inválida.")
            return redirect("assessment", year=year)
        # Ticket 26 (P0 do auditor): a reabertura devolve o prejuízo
        # consumido no fechamento — compensações do ano retornam ao saldo
        # de origem e o snapshot é removido na MESMA transação (indivisível).
        from fiscal.losses import LossLedgerService
        with transaction.atomic():
            devolvido = LossLedgerService.revert_compensations(year)
            apagados, _ = AnnualAssessment.objects.filter(year=year).delete()
        if not apagados:
            messages.warning(request, f"Ano {year} já está em aberto.")
        else:
            msg = (
                f"Ano {year} reaberto — snapshot de fechamento removido. "
                "Refaça a apuração e feche o ano novamente."
            )
            if devolvido:
                msg += f" Prejuízo devolvido ao saldo: R$ {devolvido}."
            messages.warning(request, msg)
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
