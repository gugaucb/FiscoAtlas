# 01: Corrigir UnboundLocalError na criptografia do banco no setup

**What to build:** Ao concluir o setup inicial em /configurar/, o sistema criptografa o banco principal sem erro 500 (UnboundLocalError: `os` usado antes do import) e o usuário é direcionado à tela de recovery key / sistema desbloqueado.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Teste reproduz a falha: criptografia de um banco plaintext file-based roda sem UnboundLocalError e produz arquivo cifrado legível com a VaultKey
- [ ] Imports de `os`/`shutil` resolvidos no escopo correto
- [ ] Suite completa 100% green
- [ ] Usuário consegue desbloquear com a senha definida no setup e o db.sqlite3 real fica cifrado
