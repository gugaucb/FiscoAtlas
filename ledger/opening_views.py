from django.contrib import messages
from django.urls import reverse_lazy
from django.views import generic

from ledger.models import OpeningPosition
from ledger.opening_forms import OpeningPositionForm


class OpeningPositionView(generic.ListView):
    model = OpeningPosition
    template_name = "ledger/opening_position.html"
    context_object_name = "openings"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = OpeningPositionForm()
        return ctx


class OpeningPositionCreateView(generic.CreateView):
    form_class = OpeningPositionForm
    template_name = "ledger/opening_position.html"
    success_url = reverse_lazy("opening-position")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["openings"] = OpeningPosition.objects.all()
        ctx["form"] = self.get_form()
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Posição de abertura registrada.")
        return super().form_valid(form)
