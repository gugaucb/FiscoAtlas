from django import forms
from django.shortcuts import redirect
from django.views import generic

from fiscal.models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["name", "cpf", "tax_residency_status", "residency_start_date",
                  "residency_end_date", "has_dsdp"]
        labels = {
            "name": "Nome completo",
            "cpf": "CPF",
            "tax_residency_status": "Condição de residência fiscal",
            "residency_start_date": "Início da residência",
            "residency_end_date": "Fim da residência (se aplicável)",
            "has_dsdp": "Houve mudança de residência (DSDP) no período",
        }
        widgets = {
            "residency_start_date": forms.DateInput(attrs={"type": "date"}),
            "residency_end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # default do modelo (UNKNOWN): ausência de resposta não bloqueia o form
        self.fields["tax_residency_status"].required = False


class ProfileView(generic.FormView):
    template_name = "fiscal/perfil.html"
    form_class = ProfileForm
    success_url = "/perfil/"

    def get_initial(self):
        profile = Profile.objects.first()
        if profile:
            return {f: getattr(profile, f) for f in
                    ("name", "cpf", "tax_residency_status", "residency_start_date",
                     "residency_end_date", "has_dsdp")}
        return {}

    def form_valid(self, form):
        profile = Profile.objects.first()
        if profile:
            for f in ("name", "cpf", "tax_residency_status", "residency_start_date",
                      "residency_end_date", "has_dsdp"):
                setattr(profile, f, form.cleaned_data[f])
            profile.save()
        else:
            form.save()
        return redirect(self.success_url)
