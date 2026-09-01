# 01: Lock real — sessão não vale desbloqueio sem a VaultKey em memória

**What to build:** Com o navegador apontando para um servidor/container reiniciado (chave fora da memória), qualquer página redireciona para /bloqueado/ (tela de lock limpa) em vez do traceback "Banco cifrado e aplicação bloqueada". O middleware passa a exigir sessão desbloqueada E VaultKey em memória; sem a chave, a sessão é limpa e o usuário desbloqueia normalmente.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [ ] Unit: sessão com UNLOCKED_KEY + sem VaultKey em memória → redirect /bloqueado/ e sessão limpa
- [ ] Unit: sessão com UNLOCKED_KEY + VaultKey em memória → request passa (comportamento atual)
- [ ] Unit: auto-lock também limpa a checagem coerentemente
- [ ] E2E/fluxo real: container reiniciado com cookie antigo → /bloqueado/ 200, sem traceback
