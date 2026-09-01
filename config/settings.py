import os
import dj_database_url

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-not-secret")
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "fiscal",
    "fx",
    "ledger",
    "security",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "security.middleware.VaultLockMiddleware",
]

ROOT_URLCONF = "config.urls"

_DATABASE = dj_database_url.config(default="sqlite:///db.sqlite3")
DATABASES = {
    # Banco principal: cifrado com SQLCipher (chave = VaultKey em memória)
    "default": {**_DATABASE, "ENGINE": "security.sqlcipher_backend"},
    # Vault de chaves: só material wrappado e parâmetros KDF (nada plaintext sensível);
    # precisa ser acessível mesmo com a aplicação bloqueada.
    "vault": {"ENGINE": "django.db.backends.sqlite3", "NAME": "vault.sqlite3"},
}
# Em testes o vault mora no banco de teste default (mesma base, sem alias separado)
import sys

SECURITY_VAULT_ALIAS = "default" if "pytest" in sys.modules else "vault"

DATABASE_ROUTERS = ["security.router.SecurityRouter"]

# Sessão sem dependência do banco principal (evita deadlock no desbloqueio)
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

USE_TZ = True
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"

STATIC_URL = "static/"
AUTO_LOCK_TIMEOUT_MINUTES = 10  # bloqueio automático por inatividade
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
    ]},
}]
