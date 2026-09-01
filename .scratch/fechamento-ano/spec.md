# Spec — Fechamento de ano

## Problema

O motor fiscal só herda prejuízo de anos anteriores se existir o `AnnualAssessment`
(snapshot) do ano anterior — hoje salvável apenas via shell. O usuário precisa de um
fluxo claro de fechamento na tela, e de visibilidade do estado de fechamento para
entender a compensação entre anos.

## Decisões

- Fechamento = salvar snapshot do ano (`update_or_create` já existente no motor);
  reabrir/re-fechar é permitido e recalcula.
- Fechado não trava nada: é marca de que aquele ano foi conferido e consolidado.
- Relatório e apuração comunicam o estado (fechado / não fechado) e avisam quando o
  ano anterior não foi fechado, pois o saldo a compensar herdado pode estar incompleto.

## Slices

1. Botão "Fechar ano" na apuração (salva snapshot com confirmação).
2. Status de fechamento nas telas + aviso no relatório quando o ano anterior não
   está fechado.
