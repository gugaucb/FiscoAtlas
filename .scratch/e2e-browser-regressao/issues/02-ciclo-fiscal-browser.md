# 02: Ciclo fiscal completo por browser — apuração → reconciliação → fechamento → DIRPF

**What to build:** Como usuário final pelo browser: executar a apuração anual do cenário rico (ticket 01), documentar saldos documentais, classificar todos os impostos exteriores, fechar o ano 2026 (dialog confirm) e gerar o relatório DIRPF (HTML + PDF) e memória de cálculo. Valores esperados explícitos gravados no teste — regressão de verdade, não comparação relativa.

**Blocked by:** 01 (cenário rico).

**Status:** ready-for-agent

- [ ] Apuração 2026 executada por UI com rendimento bruto, perdas, base tributável e IR (15%) iguais aos valores calculados manualmente no cenário
- [ ] Saldos documentais documentados via /documentar-saldos/ para ambas as contas (caixa conferindo com o ledger — dividendo entra LÍQUIDO)
- [ ] Todos os ForeignTaxPayments classificados (recoverability_status) via tela de edição
- [ ] Fechamento do ano 2026 concluído por UI (dialog handler registrado) — badge de ano fechado visível
- [ ] Relatório DIRPF gerado (HTML) e PDF baixável; memória de cálculo PDF disponível
- [ ] Validação de transferência solitária coberta: fechamento com par IN/OUT incompleto é bloqueado; com o par completo, passa
- [ ] Testes verificam valores com tolerância de centavos, nunca "maior que zero"