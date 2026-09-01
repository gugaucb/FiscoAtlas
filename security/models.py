from django.db import models


class SecuritySettings(models.Model):
    """Configurações do vault. Nunca armazena chaves em plaintext — apenas
    material wrappado (pela KEK da senha ou pela recovery key) e parâmetros KDF."""

    crypto_version = models.PositiveIntegerField(default=1)
    argon2_salt = models.BinaryField()
    argon2_memory_cost = models.PositiveIntegerField(default=65536)
    argon2_iterations = models.PositiveIntegerField(default=3)
    argon2_parallelism = models.PositiveIntegerField(default=4)
    wrapped_vault_key_password = models.BinaryField(null=True, blank=True)
    wrapped_vault_key_recovery = models.BinaryField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get(cls):
        return cls.objects.first()


class SecurityAuditLog(models.Model):
    """Trilha de auditoria: só identificadores opacos, nunca dados sensíveis."""
    timestamp = models.DateTimeField()
    event_type = models.CharField(max_length=64)
    resource_type = models.CharField(max_length=64, blank=True, default="")
    resource_id = models.CharField(max_length=128, blank=True, default="")
    status = models.CharField(max_length=32, default="OK")
    metadata_safe = models.JSONField(default=dict)
    event_hash = models.CharField(max_length=64, blank=True, default="")


class EncryptedDocument(models.Model):
    """Documento cifrado em repouso. FileKey wrappada pela VaultKey;
    nome do arquivo também cifrado; hash para verificação de integridade."""
    encrypted_filename = models.BinaryField()
    wrapped_file_key = models.BinaryField()
    file_path = models.CharField(max_length=512)
    file_hash = models.CharField(max_length=64)
    crypto_version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
