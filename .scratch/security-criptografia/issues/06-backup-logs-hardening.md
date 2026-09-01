# 06: Backup cifrado + exportação segura + hardening de logs

**What to build:** Comando/tela de backup gera pacote contendo apenas material
cifrado (banco cifrado, documentos .enc, wrapped keys) — restaure-o em outra
máquina e ele continua exigindo senha ou recovery key. Exportações fiscais (PDF)
nunca persistem em plaintext. Auditoria ganha hash chaining e eventos de
backup/restore. Filtro garante que CPF/senha/chaves/valores nunca apareçam em logs.

**Blocked by:** 04 e 05.

**Status:** resolved

- [x] Backup contém só material cifrado (nunca backup_plaintext.db)
- [x] Backup copiado para pendrive/nuvem permanece ilegível sem senha/recovery
- [x] Restauração exige desbloqueio com chave correta
- [x] PDFs de exportação gerados em memória, sem persistência em plaintext
- [x] Hash chaining na trilha de auditoria (alteração retroativa detectável)
- [x] Eventos BACKUP_CREATED / RESTORE_EXECUTED na auditoria
- [x] Testes: backup restaurado exige chave, tampering no log detectado, sem dados sensíveis em logs
