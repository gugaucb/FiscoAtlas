# 03: Regenerar recovery key

**What to build:** Usuário desbloqueado acessa /seguranca/ e regenera a recovery key (para casos como a atual, gerada mas nunca exibida). A nova é exibida uma única vez; a antiga deixa de valer; a senha continua funcionando; evento RECOVERY_REGENERATED no audit log.

**Blocked by:** 01 (runsecure boot travado).

**Status:** resolved

- [ ] VaultService.regenerate_recovery_key(vault_key): formato 6×4, rewrap, senha válida, recovery antiga inválida
- [ ] GET /seguranca/ com status + formulário (exige unlock)
- [ ] POST /seguranca/recovery/regenerar/ exibe a chave uma única vez; travado → redirect /bloqueado/
- [ ] SecurityAuditLog com RECOVERY_REGENERATED, sem a chave no metadata
- [ ] Suite green
