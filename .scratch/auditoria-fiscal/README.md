# auditoria-fiscal — backlog de correção fiscal

Origem: auditoria externa (ChatGPT como auditor contábil) sobre o código fiscal do
FiscoAtlas. Cada alegação foi **validada contra o código real** antes de virar ticket.
Vereditos e evidências (file:line) estão no histórico da conversa; este README registra
o que foi adotado, o que foi descartado e as regras de execução.

## Status do tracker

- Todos os tickets estão `ready-for-agent` (nenhum blocker pendente inicial).
- As dependências em `Blocked by` são **edges reais** validadas, não uma sequência linear.

## Regra de ouro (vale para todos os tickets)

1. **Não adaptar a implementação para manter testes fiscalmente incorretos.** Quando um
   teste existente contradisser a regra corrigida, substitua o teste e documente
   explicitamente por que o comportamento anterior estava errado.
2. Cada correção deve ter **teste de regressão que falha no código atual** e passa
   somente após a implementação.
3. **Sem fallback silencioso** para dados fiscais desconhecidos: dados faltantes ou
   ambíguos produzem estado `PRELIMINAR`, `UNDETERMINED` ou bloqueiam o fechamento,
   conforme o caso.
4. Valores esperados nos testes devem ser **calculados explicitamente** (não comparar
   dois métodos do próprio sistema).

## O que NÃO foi adotado do relatório (e por quê)

1. **"DARF < R$10 é tratado como imposto extinto"** — exagero. O código já acumula o
   valor no ajuste anual (`fiscal/darf.py:47`); o problema é a nomenclatura
   ("dispensado") e a citação do artigo errado. Corrigir semântica + referência, não
   "reconstruir o DARF".
2. **Reconstrução do ano fiscal do `TaxEngine` para a "data fiscal efetiva" em tudo** —
   errado para ganhos: a trade_date é o fato gerador correto no IRPF para
   alienações. Fatiado como slice estreito (ticket 10: rendimentos e imposto exterior).
3. **`AssetValuation` com tela/formulário/fluxo de confirmação completo** —
   superdimensionado. Versão mínima no ticket 07: valor de mercado na data-base
   informado pelo usuário, com flag de confirmado.
4. **`FilingRule` proposto duas vezes com designs diferentes** (P0.4 e P1.3) — unificado
   num único modelo versionado por exercício (ticket 08).
5. **Pacote ImportIssue + workflow de resolução + reconciliação + 2 modelos de statement
   documental de uma vez** — fatiado: importador/ImportIssue (01), reconciliação +
   integração ao fechamento (12).
6. **Sequência linear P0-01→P2-02** — serializa trabalho independente sem ganho de
   segurança. Edges reais:
   - 01 Importador ─┬─→ 12 Reconciliação (ImportIssue PENDING bloqueia fechamento)
   - 04 ForeignTaxPayment ─┬─→ 05 Crédito exterior ─┬─→ 13 Suíte adversarial
   -                        ├─→ 10 Datas fiscais      │
   - 06 Ownership ─→ 07 CBE v2 ─────────────────────┤
   - 02 Referências legais ─→ 08 DARF/FilingRule ───┤
   - 03 OpeningPosition ────────────────────────────┘

## Dependências adotadas do item 6 do auditor

- **ImportIssue → Reconciliação → Bloqueio de fechamento**: `AnnualClosingValidator`
  não pode bloquear por `ImportIssue PENDING` antes de existir o mecanismo que os cria
  (ticket 01). O bloqueio é critério de aceite do ticket 12.
- **Separação de responsabilidades**: `AnnualReconciliationService` ("os dados de
  entrada estão completos e conciliados?") fica separado do `AnnualClosingValidator`
  ("os dados conciliados atendem às regras fiscais?"), executados nessa ordem no
  `CloseYearView`.
- **Critério de pendência por ano-calendário**: pendências bloqueiam por eventos com
  data no ano fechado (uma linha antiga pode virar pendência descoberta só depois);
  não por um campo `fiscal_year` no issue.

## Ordem de execução sugerida

Trabalhar a fronteira (ticket cujos blockers estão todos fechados). Começar por
01 (defeito capaz de eliminar fato tributável do sistema), 02, 03, 04, 06, 09, 11
(sem bloqueios); depois 05, 07, 08, 10; por fim 12 e 13.
