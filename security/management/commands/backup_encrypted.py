"""Backup cifrado: contém apenas material cifrado + wrapped keys (nunca plaintext)."""
import base64
import json
import os
import zipfile

from django.conf import settings
from django.core.management.base import BaseCommand

from security.audit import log_event
from security.models import EncryptedDocument, SecuritySettings


def make_backup(out_path: str, db_path: str | None = None) -> None:
    svc = SecuritySettings.get()
    db_path = db_path or settings.DATABASES["default"]["NAME"]
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        # banco já é SQLCipher cifrado — cópia byte a byte permanece cifrada
        z.write(db_path, "db.sqlite3.enc")
        meta = {"crypto_version": 1, "wrapped_keys": {}}
        if svc:
            meta["wrapped_keys"] = {
                "password": base64.b64encode(bytes(svc.wrapped_vault_key_password or b"")).decode(),
                "recovery": base64.b64encode(bytes(svc.wrapped_vault_key_recovery or b"")).decode(),
                "argon2_salt": base64.b64encode(bytes(svc.argon2_salt)).decode(),
                "memory_cost": svc.argon2_memory_cost,
                "iterations": svc.argon2_iterations,
                "parallelism": svc.argon2_parallelism,
            }
        z.writestr("metadata.json", json.dumps(meta))
        for doc in EncryptedDocument.objects.all():
            if os.path.exists(doc.file_path):
                z.write(doc.file_path, "documents/" + os.path.basename(doc.file_path))
    log_event("BACKUP_CREATED", resource_type="backup", resource_id=os.path.basename(out_path))


class Command(BaseCommand):
    help = "Gera backup contendo apenas material cifrado (banco SQLCipher + documentos .enc + wrapped keys)."

    def add_arguments(self, parser):
        parser.add_argument("out_path")
        parser.add_argument("--db", default=None, help="Caminho do banco a incluir (padrão: banco principal)")

    def handle(self, *args, **options):
        make_backup(options["out_path"], db_path=options.get("db"))