from django import forms
from django.shortcuts import redirect
from django.views import generic

from fiscal.models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["name", "cpf"]
        labels = {"name": "Nome completo", "cpf": "CPF"}


class ProfileView(generic.FormView):
    template_name = "fiscal/perfil.html"
    form_class = ProfileForm
    success_url = "/perfil/"

    def get_initial(self):
        profile = Profile.objects.first()
        if profile:
            return {"name": profile.name, "cpf": profile.cpf}
        return {}

    def form_valid(self, form):
        profile = Profile.objects.first()
        if profile:
            profile.name = form.cleaned_data["name"]
            profile.cpf = form.cleaned_data["cpf"]
            profile.save()
        else:
            form.save()
        return redirect(self.success_url)
