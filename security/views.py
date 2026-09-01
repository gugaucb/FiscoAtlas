from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import generic

from security import state
from security.audit import log_event
from security.vault import InvalidPassword, VaultLocked, VaultService


def _close_db_connections():
    """Fecha conexões file-based (forçando reconexão com a chave).
    Bancos in-memory (testes) perdem as tabelas se todas as conexões fecharem."""
    from django.db import connections
    for conn in connections.all():
        name = str(conn.settings_dict.get("NAME") or "")
        if "memory" not in name and not conn.is_in_memory_db():
            conn.close()

# Sessão guarda apenas prova de desbloqueio — nunca a VaultKey em si.
UNLOCKED_KEY = "vault_unlocked_at"


class LockView(generic.View):
    def get(self, request):
        if request.session.get(UNLOCKED_KEY):
            return redirect("/")
        if not VaultService().is_configured():
            return render(request, "security/setup.html")
        return render(request, "security/lock.html")

    def post(self, request):
        # A tela de setup é renderizada em /bloqueado/ e o formulário envia
        # para a própria URL; delega conforme o estado do vault.
        if VaultService().is_configured():
            return UnlockView().post(request)
        return SetupView().post(request)


class SetupView(generic.View):
    """Primeiro acesso: define a senha e exibe a recovery key uma única vez."""

    def post(self, request):
        svc = VaultService()
        if svc.is_configured():
            return redirect("lock")
        password = request.POST.get("password", "")
        if len(password) < 8:
            return render(request, "security/setup.html",
                          {"error": "A senha deve ter pelo menos 8 caracteres."})
        if password != request.POST.get("password2"):
            return render(request, "security/setup.html",
                          {"error": "As senhas não coincidem."})
        recovery = svc.setup(password)
        vault_key = svc.unlock_with_password(password)
        state.set_vault_key(vault_key)
        _encrypt_main_database_if_plaintext()
        request.session[UNLOCKED_KEY] = True
        log_event("LOGIN_SUCCESS", metadata_safe={"method": "setup"})
        log_event("DATABASE_UNLOCKED")
        return render(request, "security/setup_done.html",
                      {"recovery": recovery}, status=200)


def _encrypt_main_database(db_path):
    """Criptografa um banco plaintext com a VaultKey atual (idempotente)."""
    import os
    import shutil

    from security.database import rekey_main_database
    from security.sqlcipher_backend.base import is_plaintext_or_new

    if not is_plaintext_or_new(db_path) or os.path.getsize(db_path) == 0:
        return
    tmp = db_path + ".enc.tmp"
    rekey_main_database(db_path, tmp, state.get_vault_key())
    shutil.move(tmp, db_path)


def _encrypt_main_database_if_plaintext():
    """Migração one-time: banco plaintext → SQLCipher com a VaultKey."""
    from django.conf import settings

    db_path = settings.DATABASES["default"]["NAME"]
    if not db_path or db_path == ":memory:":
        return
    if settings.SECURITY_VAULT_ALIAS == "default":  # ambiente de teste
        return
    _encrypt_main_database(db_path)


class UnlockView(generic.View):
    def post(self, request):
        svc = VaultService()
        try:
            if request.POST.get("recovery_key"):
                vault_key = svc.unlock_with_recovery(request.POST["recovery_key"])
                log_event("LOGIN_SUCCESS", metadata_safe={"method": "recovery"})
                log_event("RECOVERY_USED")
            elif request.POST.get("password"):
                vault_key = svc.unlock_with_password(request.POST["password"])
                log_event("LOGIN_SUCCESS", metadata_safe={"method": "password"})
            else:
                raise InvalidPassword("Informe a senha")
            # chave só em memória; conexões do banco principal reabrem com PRAGMA key
            state.set_vault_key(vault_key)
            _close_db_connections()
            request.session[UNLOCKED_KEY] = True
            # reinicia o relógio de inatividade: last_activity velho (sessão
            # persistente após um auto-lock) causaria auto-lock imediato
            from django.utils import timezone
            request.session["vault_last_activity"] = timezone.now().isoformat()
            log_event("DATABASE_UNLOCKED")
            return redirect("/")
        except (InvalidPassword, VaultLocked):
            log_event("LOGIN_FAILED", status="DENIED",
                      metadata_safe={"method": "recovery" if request.POST.get("recovery_key") else "password"})
            return render(request, "security/lock.html",
                          {"error": "Senha ou recovery key incorreta."}, status=200)


class LockNowView(generic.View):
    def post(self, request):
        request.session.pop(UNLOCKED_KEY, None)
        request.session.cycle_key()
        state.clear_vault_key()
        _close_db_connections()
        log_event("DATABASE_LOCKED")
        return redirect(reverse("lock"))


class SecurityHomeView(generic.TemplateView):
    template_name = "security/security_home.html"


class RegenerateRecoveryView(generic.View):
    def post(self, request):
        vault_key = state.get_vault_key()
        if not vault_key:
            return redirect("lock")
        recovery = VaultService().regenerate_recovery_key(vault_key)
        log_event("RECOVERY_REGENERATED")
        return render(request, "security/setup_done.html", {"recovery": recovery})
