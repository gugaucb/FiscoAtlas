# 01: PTAX de fechamento (31/12) manual na aba Relatório

**What to build:** Ao abrir o Relatório de um ano cuja PTAX de 31/12 o BCB ainda não tem (ex.: 31/12/2026, data futura), a página exibe um formulário inline "PTAX de fechamento" (valor + motivo) em vez do erro genérico. Ao confirmar, a taxa é registrada como override manual e o relatório (HTML e os dois PDFs) renderiza normalmente com ela. Se o BCB já tem a cotação, o form não aparece; override já cadastrado tem prioridade sobre a API; motivo obrigatório.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [ ] GET do relatório com PTAX de 31/12 indisponível mostra o form inline (não a página de erro genérica)
- [ ] POST registra override manual (reuso do mecanismo existente) e redireciona de volta ao relatório renderizado com o valor informado
- [ ] Motivo vazio → erro de validação, sem gravar
- [ ] GET com cotação do BCB em cache (ou override já existente) não mostra o form
- [ ] O PDF do relatório DIRPF (e os saldos BRL na tela) saem com a taxa informada
- [ ] Unit: endpoint cobrindo os 4 cenários acima
- [ ] E2E browser: relatório 2026 → informar PTAX → HTML e PDFs renderizam com o valor informado
