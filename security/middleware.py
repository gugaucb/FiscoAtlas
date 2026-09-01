from django.shortcuts import redirect
from django.utils import timezone

from security.audit import log_event

# Rotas acessíveis com a aplicação bloqueada.
PUBLIC_PATHS = {"/bloqueado/", "/desbloquear/", "/configurar/"}
UNLOCKED_KEY = "vault_unlocked_at"  # igual a security.views.UNLOCKED_KEY
LAST_ACTIVITY_KEY = "vault_last_activity"
AUTO_LOCK_TIMEOUT_MINUTES = 10  # configurável via AUTO_LOCK_TIMEOUT_MINUTES no settings


class VaultLockMiddleware:
    """Exige sessão desbloqueada para qualquer tela do sistema;
    bloqueia automaticamente após inatividade."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if request.path.startswith("/static/") or path in PUBLIC_PATHS:
            return self.get_response(request)
        if not request.session.get(UNLOCKED_KEY):
            return redirect("/bloqueado/")
        if self._expired(request):
            request.session.pop(UNLOCKED_KEY, None)
            request.session.cycle_key()
            log_event("DATABASE_LOCKED", metadata_safe={"reason": "auto-lock"})
            return redirect("/bloqueado/")
        request.session[LAST_ACTIVITY_KEY] = timezone.now().isoformat()
        return self.get_response(request)

    def _expired(self, request) -> bool:
        from django.conf import settings as dj_settings

        timeout = getattr(dj_settings, "AUTO_LOCK_TIMEOUT_MINUTES", AUTO_LOCK_TIMEOUT_MINUTES)
        last = request.session.get(LAST_ACTIVITY_KEY)
        if not last:
            return False
        from datetime import timedelta
        return timezone.now() - timezone.datetime.fromisoformat(last) > timedelta(minutes=timeout)
