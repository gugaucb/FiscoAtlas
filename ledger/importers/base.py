"""Base dos importadores de extratos CSV (RF-IMP-001..004)."""
import hashlib
from datetime import datetime


class StatementImportError(ValueError):
    pass


def parse_date_us(value: str):
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise StatementImportError(f"data inválida: {value!r}")


class StatementImporter:
    """Classe base: deduplicação por hash + criação via EventService."""

    source = "GENERIC"

    def __init__(self, account):
        self.account = account

    def file_hash(self, text: str) -> str:
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    def already_imported(self, file_hash: str) -> bool:
        from ledger.models import ImportBatch
        return ImportBatch.objects.filter(file_hash=file_hash).exists()

    def import_csv(self, text: str):
        raise NotImplementedError
