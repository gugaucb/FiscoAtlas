# 03: Login local + bloqueio manual + auto-lock + auditoria

**What to build:** Ao abrir o sistema, todas as telas exigem desbloqueio (senha ou
recovery key). Botão "Bloquear" volta à tela bloqueada descartando a chave da
memória. Inatividade configurável bloqueia automaticamente. Eventos de segurança
(login, desbloqueio, bloqueio) registrados em trilha de auditoria sem dados sensíveis.

**Blocked by:** 02.

**Status:** resolved

- [x] Tela de bloqueio/login; sem sessão desbloqueada, nenhuma tela do sistema responde
- [x] Desbloqueio por senha ou recovery key; falhas registradas
- [x] Botão "Bloquear aplicação": chave descartada, interface volta ao bloqueio
- [x] Auto-lock por inatividade (configurável, padrão 10 min)
- [x] Tabela security_audit_log (LOGIN_SUCCESS/FAILED, DATABASE_UNLOCKED/LOCKED, RECOVERY_USED)
- [x] Logs não contêm senha, recovery key, chaves, CPF ou valores
- [x] Testes cobrem bloqueio, desbloqueio válido/inválido e trilha de auditoria
