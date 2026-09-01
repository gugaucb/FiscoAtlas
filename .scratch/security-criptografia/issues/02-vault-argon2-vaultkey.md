# 02: Vault — Argon2id + VaultKey + Recovery Key + troca de senha

**What to build:** Primeiro acesso do usuário: define uma senha, o sistema gera a
VaultKey aleatória de 256 bits e a protege via Argon2id (KEK da senha) e via
Recovery Key exibida uma única vez. A VaultKey nunca fica em plaintext em disco.
Trocar senha ou usar a recovery key apenas re-wrappa a VaultKey — o conteúdo
protegido continua válido.

**Blocked by:** 01.

**Status:** ready-for-agent

- [ ] Setup inicial: senha do usuário → Argon2id (salt + parâmetros persistidos) → KEK → wrap VaultKey
- [ ] Recovery key de alta entropia gerada, exibida uma única vez, nunca armazenada em plaintext
- [ ] VaultKey desbloqueável por senha OU recovery key; incorretas falham
- [ ] Troca de senha: rewrap com nova KEK, dados protegidos continuam decifráveis
- [ ] Recuperação: recovery key desbloqueia e permite definir nova senha
- [ ] Modelo security_settings com crypto_version e parâmetros Argon2 (nenhuma chave em plaintext)
- [ ] Testes: senha/recovery corretas abrem, incorretas falham, troca de senha preserva dados
