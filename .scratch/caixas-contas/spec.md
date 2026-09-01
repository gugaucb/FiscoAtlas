# Spec — Caixas/Contas nomeáveis

## Problema

O sistema não tem telas para gerenciar contas (BrokerAccount): são criadas via shell.
Brokers oferecem normalmente conta de investimento e conta corrente; o usuário
precisa criar, nomear e tipar caixas pela interface.

## Decisões de escopo

- Campo de apelido livre (nome do caixa) além de corretora/número.
- Tipo: Cash/Custódia (choices já existentes); flag remunerada mantida — é ela
  que carrega o efeito fiscal.
- Legislação aplicável (já implementada no motor, apenas expor na UI):
  - Caixa não remunerado: variação cambial isenta (IN RFB 2180/2024, art. 3º).
  - JUROS/rendimento: só válido em conta remunerada.
- Dados nunca apagados (spec §9): desativação lógica (`active=False`).

## Slices

1. Tela de criação de caixa/conta (apelido, corretora, número, tipo, remuneração).
2. Edição e desativação de conta (sem quebrar histórico).
3. Marcação legislativa nas telas (selos na Caixa; mensagem amigável de JUROS).
