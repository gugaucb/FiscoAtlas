from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import generic

from ledger.account_forms import BrokerAccountForm
from ledger.models import BrokerAccount


class AccountListView(generic.ListView):
    model = BrokerAccount
    template_name = "ledger/accounts.html"
    context_object_name = "accounts"

    def get_queryset(self):
        return BrokerAccount.objects.order_by("active", "name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault("form", BrokerAccountForm())
        return ctx

    def post(self, request, *args, **kwargs):
        form = BrokerAccountForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Conta criada.")
            return redirect("accounts")
        self.object_list = self.get_queryset()
        ctx = self.get_context_data(form=form)
        return self.render_to_response(ctx)


class AccountUpdateView(generic.UpdateView):
    form_class = BrokerAccountForm
    template_name = "ledger/account_edit.html"
    success_url = reverse_lazy("accounts")
    queryset = BrokerAccount.objects.all()

    def form_valid(self, form):
        messages.success(self.request, "Conta atualizada.")
        return super().form_valid(form)


class AccountDeactivateView(generic.View):
    def post(self, request, pk):
        acct = BrokerAccount.objects.get(pk=pk)
        acct.active = False
        acct.save()
        messages.success(request, "Conta desativada; histórico preservado.")
        return redirect("accounts")
