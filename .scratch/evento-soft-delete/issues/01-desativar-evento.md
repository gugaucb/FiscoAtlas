# 01: Desativar evento (soft delete)

**What to build:** Na aba Eventos, cada linha ganha um link "excluir" com confirmação; ao confirmar, o evento fica inativo (active=False) e deixa de ser contabilizado em tudo — posições, caixa, apuração, relatórios e PDFs. O registro permanece no banco (auditoria), apenas some da listagem. Mesmo padrão do "corrigir evento", que já desativa o original. Evento desativado que era correção de outro não reativa o original.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [ ] Link "excluir" em cada linha da aba Eventos, com confirmação antes do POST
- [ ] POST desativa (active=False); registro permanece no banco; linha some da listagem
- [ ] Evento desativado sai de posições, caixa, apuração, relatório e PDFs (todas as consultas já filtram active=True)
- [ ] Unit: POST desativa; consulta de posição/caixa ignora o evento desativado; nada é fisicamente deletado
- [ ] E2E: criar BUY → excluir → linha some da lista e Posições/Caixa não contabilizam
