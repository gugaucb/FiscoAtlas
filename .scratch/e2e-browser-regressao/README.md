# E2E browser de regressão — cobertura completa como usuário final

Objetivo: suíte Playwright que percorre o FiscoAtlas como o usuário final (browser),
com um cenário rico (≥5 stocks + 2 ETFs, 2 contas) e valores esperados explícitos,
armazenada como regressão futura.

## Tickets

| NN | Título | Blocked by |
|----|--------|-----------|
| 01 | Cenário rico por browser: 5 stocks + 2 ETFs em 2 contas | none |
| 02 | Ciclo fiscal completo por browser: apuração → reconciliação → fechamento → DIRPF | 01 |
| 03 | Multi-ano por browser: carry-forward, guarda de ano fechado e reabertura | 02 |
| 04 | Registros para regressão futura: valores esperados + modo de rodar | 02, 03 |

## Notas

- Transferência de custódia não tem formulário web (camada de serviço, ver manual
  seção 10): o ticket 01 semeia o par IN/OUT via `EventService`/`BrokerTransferService`
  e o teste verifica os efeitos no browser (posições nas duas contas, sem alienação
  fiscal); o ticket 02 cobre a validação de transferência solitária no fechamento.
- Regra de ouro da auditoria: valores esperados explícitos, nunca comparação
  método-a-método; sem fallback silencioso.
- Automatização Playwright: seguir as lições do CLAUDE.md (seletor específico de
  submit, input date ISO, dialog handler para fechar ano, migrate --database=vault).