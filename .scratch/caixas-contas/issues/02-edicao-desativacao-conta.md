# 02: Edição e desativação de conta

**What to build:** O usuário renomeia um caixa, corrige tipo/remuneração e pode desativar uma conta. Desativar nunca apaga dados (append-only, spec §9): a conta some das opções de novos lançamentos, mas continua integralmente em Caixa, Posições e relatórios/apuração do passado.

**Blocked by:** 01 (a tela de gestão precisa existir).

**Status:** resolved

- [ ] Editar apelido, tipo e remuneração pela tela, com atualização imediata nas telas de lançamento/caixa
- [ ] Desativar conta (ação na listagem, com confirmação); `active=False` no modelo, sem deleção
- [ ] Contas desativadas não aparecem no select de novos lançamentos
- [ ] Contas desativadas continuam na tela de Caixa e nos relatórios de anos anteriores
- [ ] Lançamentos antigos dessa conta permanecem íntegros (nenhuma query perde histórico)
- [ ] Testes cobrem edição, desativação, exclusão do select e preservação do histórico
