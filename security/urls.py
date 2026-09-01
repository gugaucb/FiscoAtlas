from django.urls import path

from security import views

urlpatterns = [
    path("bloqueado/", views.LockView.as_view(), name="lock"),
    path("configurar/", views.SetupView.as_view(), name="vault-setup"),
    path("desbloquear/", views.UnlockView.as_view(), name="unlock"),
    path("bloquear/", views.LockNowView.as_view(), name="lock-now"),
    path("seguranca/", views.SecurityHomeView.as_view(), name="security-home"),
    path("seguranca/recovery/regenerar/", views.RegenerateRecoveryView.as_view(), name="recovery-regenerate"),
]
