"""Trilha de auditoria local: eventos de segurança, nunca dados sensíveis.
Hash chaining detecta alteração retroativa no log."""
import hashlib
import json

from django.utils import timezone

from security.models import SecurityAuditLog


def _canonical(log: SecurityAuditLog) -> str:
    return json.dumps({
        "timestamp": log.timestamp.isoformat(),
        "event_type": log.event_type,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "status": log.status,
        "metadata_safe": log.metadata_safe,
    }, sort_keys=True)


def log_event(event_type: str, status: str = "OK", resource_type: str = "",
              resource_id: str = "", metadata_safe: dict | None = None):
    prev = SecurityAuditLog.objects.order_by("-id").first()
    prev_hash = prev.event_hash if prev else ""
    log = SecurityAuditLog.objects.create(
        timestamp=timezone.now(),
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        metadata_safe=metadata_safe or {},
    )
    log.event_hash = hashlib.sha256((prev_hash + _canonical(log)).encode()).hexdigest()
    log.save(update_fields=["event_hash"])
    return log


def verify_chain() -> bool:
    """Recalcula a cadeia de hashes; False se qualquer evento foi alterado/removido."""
    prev_hash = ""
    for log in SecurityAuditLog.objects.order_by("id"):
        expected = hashlib.sha256((prev_hash + _canonical(log)).encode()).hexdigest()
        if log.event_hash != expected:
            return False
        prev_hash = log.event_hash
    return True