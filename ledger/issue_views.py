"""P1 auditor: resolução de ImportIssue pela aplicação.

Nenhuma pendência criada pelo importador pode exigir alteração manual
de banco de dados para liberar o fechamento. Mínimo suficiente: vincular
o evento correspondente (RESOLVED_IMPORTED) ou ignorar com justificativa
obrigatória (RESOLVED_IGNORED) — resolved_at sempre preenchido.
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import generic

from ledger.models import BrokerAccount, FinancialEvent, ImportIssue


class ImportIssuesView(generic.View):
    template_name = "ledger/import_issues.html"

    def _context(self, account):
        issues = ImportIssue.objects.select_related("batch", "resolved_event").filter(
            batch__account=account
        ).order_by("status", "batch_id", "line_number")
        # Achado P1 do auditor (17): RESOLVED_IMPORTED com evento vinculado
        # desativado volta à lista de pendentes (re-vinculação ou ignorar)
        return {
            "account": account,
            "pendentes": [i for i in issues if i.esta_aberta],
            "resolvidos": [i for i in issues if not i.esta_aberta],
        }

    def get(self, request, account_id):
        conta = get_object_or_404(BrokerAccount, pk=account_id)
        return render(request, self.template_name, self._context(conta))

    def post(self, request, account_id):
        conta = get_object_or_404(BrokerAccount, pk=account_id)
        issue = get_object_or_404(
            ImportIssue, pk=request.POST.get("issue_pk"), batch__account=conta,
        )
        acao = request.POST.get("acao")
        try:
            if acao == "vincular":
                event_pk = (request.POST.get("event_pk") or "").strip()
                if not event_pk.isdigit():
                    raise ValueError("Informe o ID do evento lançado (número inteiro).")
                evento = FinancialEvent.objects.get(pk=int(event_pk), account=conta, active=True)
                issue.resolve_imported(evento)
                messages.success(request, f"Pendência linha {issue.line_number}: evento #{evento.pk} vinculado.")
            elif acao == "ignorar":
                issue.resolve_ignored(request.POST.get("justificativa") or "")
                messages.warning(
                    request,
                    f"Pendência linha {issue.line_number} ignorada com justificativa registrada.",
                )
            else:
                raise ValueError("Ação inválida.")
        except (ValueError, FinancialEvent.DoesNotExist) as e:
            messages.error(request, str(e))
        return redirect("import-issues", account_id=account_id)
