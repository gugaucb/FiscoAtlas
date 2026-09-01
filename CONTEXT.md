# CONTEXT.md — Glossário

Vocabulário canônico do domínio. Sem detalhes de implementação.

## Termos

### Evento Financeiro (FinancialEvent)
Registro atômico e imutável de um fato econômico (aporte, compra, venda, rendimento, taxa). Nunca é apagado; correções criam nova versão. Todo evento nasce de um documento original ou de entrada manual e mantém rastreabilidade até a fonte.

### PTAX Fiscal
A cotação PTAX escolhida por regra do exercício (tipo e data de fallback configuráveis) usada para converter eventos USD → BRL. Distinta da **taxa efetiva de câmbio** do aporte, que é apenas financeira e nunca determina custo fiscal.

### Custo Fiscal de Aquisição (acquisition_cost_brl)
Valor bruto do ativo em BRL mais despesas de aquisição convertidas pela PTAX Fiscal da data da compra. Nunca derivado do câmbio do aporte nem do valor de mercado.

### Custo Médio (average_cost_brl)
Custo fiscal total da posição dividido pela quantidade, recalculado a cada compra. Vendas **não** alteram o custo médio dos ativos remanescentes. Método padrão: custo médio ponderado (WEIGHTED_AVERAGE_COST).

### Resultado de Alienação (capital_result_brl)
Valor líquido de venda em BRL menos o custo fiscal alocado da quantidade vendida. Positivo = **Ganho**; negativo = **Prejuízo Compensável**.

### Prejuízo Compensável (LossCarryforward)
Prejuízo de alienações apurado em BRL, acumulado por ano de origem, usado para reduzir a base tributável de exercícios seguintes, dentro dos limites da regra do ano.

### Rendimento (IncomeEvent)
Dividendo, juro ou cupom recebido, registrado pelo regime de **caixa** (data do crédito efetivo), com bruto, imposto retido no exterior e líquido, todos em USD e BRL.

### Crédito de Imposto Estrangeiro
Imposto retido no exterior aproveitável contra o imposto brasileiro, limitado por rendimento ao imposto brasileiro de referência. O excedente é reportado, mas não aproveitado.

### Ano-Calendário (TaxYear)
Exercício fiscal com regras tributárias versionadas e próprias. Estados: aberto, em revisão, fechado. Fechamento nunca altera operações.

### Regra Tributária (TaxRule)
Conjunto de parâmetros fiscais de um ano-calendário (faixas de alíquota, tratamento de caixa não remunerado, compensação de prejuízos), armazenado como **dados versionados**, nunca codificado no sistema.

### Snapshot 31/12 (CashSnapshot / PositionSnapshot)
Fotografia anual de caixa e posições na data de referência, avaliados a **custo histórico em BRL** (posições) e PTAX do exercício (caixa). Valor de mercado é opcional e nunca substitui o custo fiscal.

### Ledger de Caixa (CashLedger)
Registro de movimentações de caixa por conta e moeda. Saldo esperado é sempre reconstrutível e comparável ao extrato da corretora.

### Divergência
Diferença material entre posição/saldo calculados pelo sistema e os informados pela corretora. Impede fechamento silencioso do ano.

### Importação (ImportJob)
Pipeline que transforma documento original (CSV ou PDF da corretora) em eventos revisados: nunca grava dados ambíguos sem preview e confirmação do usuário. Operações suspeitas de duplicidade vão para revisão.

### Memória de Cálculo
Explicação completa de qualquer número apresentado: operações de origem, PTAX usada, regra e versão da regra tributária, prejuízos compensados e imposto estrangeiro considerado. Obrigatória para todo resultado fiscal.

### Verificações usadas no projeto
- Este sistema é de uso pessoal (usuário único) e roda localmente via Docker.
- Ferramenta auxiliar: não transmite nada à Receita Federal e não substitui contador.
