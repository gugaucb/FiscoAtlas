"""Runserver para o banco cifrado: sobe TRAVADO, desbloqueio via navegador.

Sobrescreve check_migrations (único ponto que toca o banco no startup) e força
--noreload (o reloader reciclaria o processo e perderia a VaultKey carregada
pelo unlock web). A senha nunca passa pela linha de comando.
"""
from django.core.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):
    help = "Sobe o servidor travado; desbloqueie em /bloqueado/ pelo navegador."

    def check_migrations(self):
        pass  # banco cifrado: conexão só existe após o unlock web

    def handle(self, *args, **options):
        options["use_reloader"] = False
        addrport = options.get("args", ["127.0.0.1:8000"])[0] if options.get("args") else "127.0.0.1:8000"
        self.stdout.write(self.style.SUCCESS(
            f"Servidor travado. Desbloqueie em http://{addrport}/bloqueado/"))
        super().handle(*args, **options)
