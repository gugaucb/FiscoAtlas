from django.conf import settings

_SECURITY_APP = "security"


class SecurityRouter:
    """Modelos do app security (settings do vault + auditoria) vivem na
    base 'vault', acessível mesmo com o banco principal cifrado e travado."""

    def db_for_read(self, model, **hints):
        return settings.SECURITY_VAULT_ALIAS if model._meta.app_label == _SECURITY_APP else None

    def db_for_write(self, model, **hints):
        return settings.SECURITY_VAULT_ALIAS if model._meta.app_label == _SECURITY_APP else None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, **hints):
        if app_label == _SECURITY_APP:
            return db == settings.SECURITY_VAULT_ALIAS
        # Outros apps nunca migram na base "vault" (alias dedicado ao vault
        # de chaves), nem quando SECURITY_VAULT_ALIAS aponta para "default"
        # (testes) — migram os apps dos outros aliases de novo e queries de
        # migração via router iriam para outro alias com schema deslocado.
        return db != "vault"