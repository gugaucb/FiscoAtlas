# 02: Editar a PTAX de 31/12 no Relatório

**What to build:** Com o relatório já renderizando, a linha "PTAX 31/12" tem botão Editar que abre o mesmo formulário (valor + motivo); salvar registra novo override manual que prevalece sobre o anterior (mais recente vence). Também permite sobrescrever taxa vinda do BCB.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [ ] Linha PTAX 31/12 no relatório com botão Editar abrindo o form (valor pré-preenchido com a taxa vigente)
- [ ] POST grava novo override; relatório reflete o novo valor
- [ ] Novo override vence o anterior (mais recente por fetched_at)
- [ ] Unit: novo override prevalece; motivo vazio não grava
- [ ] E2E: informar PTAX → editar → relatório mostra o novo valor
