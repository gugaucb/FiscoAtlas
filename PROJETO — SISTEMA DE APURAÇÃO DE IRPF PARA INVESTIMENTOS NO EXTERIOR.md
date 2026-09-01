# PROJETO — SISTEMA DE APURAÇÃO DE IRPF PARA INVESTIMENTOS NO EXTERIOR

## 1. Objetivo

Desenvolver uma aplicação web para brasileiros residentes fiscais no Brasil que possuem investimentos em corretoras estrangeiras, inicialmente com foco na Avenue Securities LLC.

O sistema deverá importar, registrar, organizar e calcular operações financeiras realizadas no exterior, convertendo todos os eventos relevantes para BRL e produzindo relatórios auxiliares para preenchimento da Declaração de Ajuste Anual do IRPF.

A aplicação deverá considerar, inicialmente, as regras aplicáveis às aplicações financeiras no exterior após a Lei nº 14.754/2023 e regulamentação correspondente.

O sistema NÃO deverá transmitir declarações para a Receita Federal.

Sua função é:

- armazenar operações;
- importar documentos;
- buscar PTAX;
- calcular custo médio;
- calcular ganhos e prejuízos;
- registrar dividendos, juros e retenções;
- controlar posições;
- controlar prejuízos acumulados;
- gerar memória de cálculo;
- gerar relatórios auxiliares;
- produzir dados preparados para preenchimento da DIRPF.

Todas as regras tributárias devem ser configuráveis e versionadas por ano-calendário, pois legislação, layouts e campos da DIRPF podem mudar.

---

# 2. Escopo inicial — MVP

O MVP deverá suportar cinco eventos financeiros principais:

1. Transferência BRL → USD;
2. Compra de ativo;
3. Venda de ativo;
4. Recebimento de dividendos/juros/cupons;
5. Saldo de caixa em 31/12.

O sistema deve suportar inicialmente:

- ações;
- ETFs;
- REITs;
- bonds;
- outros ativos financeiros cadastráveis.

Corretora inicial:

- Avenue Securities LLC.

Entretanto, a arquitetura deverá permitir inclusão futura de outras corretoras sem alteração estrutural relevante.

---

# 3. Princípio fundamental do sistema

Todos os cálculos fiscais devem ser realizados em BRL.

Nunca utilizar simplesmente a valorização ou desvalorização do ativo em USD para determinar ganho tributável.

Cada operação precisa preservar:

- valor original em USD;
- data do evento;
- PTAX utilizada;
- valor convertido em BRL;
- origem da PTAX;
- memória do cálculo.

O sistema deve permitir reconstruir integralmente qualquer cálculo efetuado.

---

# 4. Regras tributárias principais

Para aplicações financeiras no exterior realizadas a partir de 01/01/2024:

- apuração anual;
- tributação consolidada na DIRPF;
- alíquota-base configurada inicialmente em 15%;
- ganhos e rendimentos são apurados em BRL;
- prejuízos compensáveis devem ser controlados;
- imposto pago no exterior pode gerar crédito dentro dos limites legais;
- não aplicar automaticamente isenção mensal equivalente à antiga regra de alienações inferiores a R$ 35.000;
- não aplicar alíquota brasileira diferenciada de day trade;
- não utilizar carnê-leão ou GCAP mensal como mecanismo padrão dessas operações;
- conta corrente estrangeira não remunerada deve possuir tratamento separado para variação cambial;
- posições patrimoniais devem utilizar custo histórico de aquisição em BRL e não valor de mercado.

As regras devem estar em um TaxRuleEngine parametrizado por ano.

Exemplo:

TaxRule:
- tax_year
- annual_rate
- foreign_tax_credit_enabled
- fx_cash_exemption
- loss_carryforward_enabled
- effective_from
- effective_until
- rule_version

Nunca deixar a alíquota de 15% codificada diretamente em diversos pontos da aplicação.

---

# 5. Usuários

Entidade:

Usuario

Campos principais:

- id
- nome
- CPF
- email
- senha/hash ou autenticação externa
- timezone
- moeda_base = BRL
- data_criacao
- data_atualizacao

O sistema deverá possuir segregação completa dos dados por usuário.

---

# 6. Ano fiscal

Criar entidade:

TaxYear

Campos:

- id
- usuario_id
- ano_calendario
- status

Status possíveis:

- ABERTO
- EM_REVISAO
- FECHADO

Um fechamento anual não deve apagar ou modificar operações.

Caso uma operação antiga seja corrigida, o sistema deverá registrar uma nova versão e recalcular os valores impactados.

---

# 7. Conta de corretora

Entidade:

BrokerAccount

Campos:

- id
- usuario_id
- broker_name
- account_number
- country_code
- currency
- account_type
- is_interest_bearing
- active

Exemplo:

broker_name = Avenue Securities LLC  
country_code = US  
currency = USD

account_type:

- CASH
- CUSTODY
- MARGIN
- OTHER

O atributo `is_interest_bearing` é importante para diferenciar caixa não remunerado de caixa remunerado.

---

# 8. Cadastro de ativos

Entidade:

Asset

Campos:

- id
- ticker
- description
- asset_type
- ISIN
- currency
- country_code
- active

asset_type:

- STOCK
- ETF
- REIT
- BOND
- FUND
- OTHER

Evitar vincular o ticker diretamente à operação sem um asset_id.

---

# 9. Modelo unificado de eventos

Recomenda-se criar uma entidade base:

FinancialEvent

Campos comuns:

- id UUID
- usuario_id
- broker_account_id
- asset_id nullable
- event_type
- trade_date
- settlement_date
- tax_date
- currency
- source
- external_reference
- imported_file_id
- notes
- created_at
- updated_at
- version
- status

event_type:

- FX_IN
- FX_OUT
- BUY
- SELL
- DIVIDEND
- INTEREST
- BOND_COUPON
- FEE
- CASH_INTEREST
- SPLIT
- SPINOFF
- CORPORATE_ACTION
- MANUAL_ADJUSTMENT

Cada evento deverá possuir dados complementares específicos.

Nunca apagar eventos financeiros permanentemente.

Implementar:

- soft delete;
- histórico de alteração;
- audit log.

---

# 10. Evento — transferência BRL → USD

Entidade ou extensão:

FxTransfer

Campos:

- event_id
- direction
- amount_brl_gross
- amount_brl_net
- amount_usd
- effective_exchange_rate
- ptax_rate
- ptax_date
- iof_brl
- fees_brl
- fees_usd
- origin_bank
- destination_account
- external_reference

direction:

BRL_TO_USD

Uso:

- reconciliação de caixa;
- rastreabilidade do funding;
- histórico de aportes.

Importante:

A transferência de BRL para USD NÃO deve determinar automaticamente o custo fiscal dos ativos posteriormente adquiridos.

O custo fiscal do ativo deve ser calculado com base na regra tributária da própria compra e sua conversão aplicável.

A taxa efetiva de câmbio pode ser armazenada para reconciliação financeira, enquanto a cotação fiscal deve permanecer separada.

---

# 11. Evento — compra

Campos:

- event_id
- asset_id
- quantity
- unit_price_usd
- gross_value_usd
- brokerage_fee_usd
- other_fees_usd
- ptax_rate
- ptax_date
- gross_value_brl
- fees_brl
- acquisition_cost_brl

Cálculo:

gross_value_usd =
quantity × unit_price_usd

gross_value_brl =
gross_value_usd × ptax_rate

fees_brl =
total_fees_usd × ptax_rate

acquisition_cost_brl =
gross_value_brl + fees_brl

A compra deve:

- aumentar quantidade;
- aumentar custo fiscal;
- recalcular custo médio;
- reduzir caixa USD.

---

# 12. Custo médio

O sistema deverá manter posição por usuário + conta + ativo.

Entidade:

AssetPosition

Campos:

- usuario_id
- broker_account_id
- asset_id
- quantity
- total_cost_brl
- average_cost_brl
- total_cost_usd
- average_cost_usd
- updated_at

Fórmula principal:

novo_custo_total_brl =
custo_total_anterior_brl + custo_compra_brl

nova_quantidade =
quantidade_anterior + quantidade_comprada

novo_custo_medio_brl =
novo_custo_total_brl / nova_quantidade

Utilizar Decimal de alta precisão.

Nunca utilizar float/double para valores monetários.

---

# 13. Evento — venda

Campos:

- event_id
- asset_id
- quantity
- unit_price_usd
- gross_value_usd
- brokerage_fee_usd
- other_fees_usd
- ptax_rate
- ptax_date
- gross_value_brl
- expenses_brl
- net_sale_value_brl
- allocated_cost_brl
- capital_result_brl

Cálculo:

gross_value_brl =
quantity × unit_price_usd × ptax_rate

expenses_brl =
fees_usd × ptax_rate

net_sale_value_brl =
gross_value_brl - expenses_brl

allocated_cost_brl =
quantity_sold × average_cost_brl_before_sale

capital_result_brl =
net_sale_value_brl - allocated_cost_brl

Se:

capital_result_brl > 0:
GAIN

capital_result_brl < 0:
LOSS

Depois da venda:

remaining_quantity =
previous_quantity - sold_quantity

remaining_cost_brl =
previous_total_cost_brl - allocated_cost_brl

A venda não deve recalcular o custo médio dos ativos remanescentes com base no preço de venda.

---

# 14. Validação de venda

O sistema não deve permitir:

quantity_sold > available_quantity

salvo quando algum tipo específico de operação permitir posição short e houver suporte explícito para isso.

No MVP:

SHORT SELLING = NÃO SUPORTADO.

---

# 15. Método de custo

Método padrão inicial:

WEIGHTED_AVERAGE_COST

Preparar arquitetura para eventualmente suportar:

FIFO

Mas não permitir alternância de método no meio de um exercício sem recalcular todo o histórico correspondente.

Campo:

cost_method

---

# 16. Evento — dividendos, juros e cupons

Entidade:

IncomeEvent

Campos:

- event_id
- asset_id
- income_type
- payment_date
- gross_usd
- foreign_tax_usd
- net_usd
- ptax_rate
- ptax_date
- gross_brl
- foreign_tax_brl
- net_brl
- external_reference

income_type:

- DIVIDEND
- INTEREST
- BOND_COUPON
- OTHER

Regime:

CAIXA.

Utilizar a data efetiva de crédito definida pela regra fiscal do exercício.

Cálculos:

gross_brl =
gross_usd × ptax_rate

foreign_tax_brl =
foreign_tax_usd × ptax_rate

net_brl =
net_usd × ptax_rate

Validar aproximadamente:

net_usd =
gross_usd - foreign_tax_usd

Permitir tolerância configurável de arredondamento.

---

# 17. Crédito de imposto estrangeiro

Não implementar simplesmente:

total_foreign_tax × abatimento integral da obrigação tributária.

Criar engine específico:

ForeignTaxCreditEngine

Ele deve guardar crédito e limite por rendimento conforme as regras tributárias vigentes.

Para cada rendimento:

brazilian_tax_reference =
gross_income_brl × applicable_tax_rate

usable_foreign_tax_credit =
min(
    foreign_tax_brl,
    brazilian_tax_reference
)

unused_foreign_tax =
foreign_tax_brl - usable_foreign_tax_credit

O valor excedente deverá aparecer no relatório, mesmo quando não puder ser utilizado.

A implementação precisa permitir mudanças futuras na forma de limitação do crédito.

---

# 18. Resultado anual

Entidade:

AnnualTaxCalculation

Campos:

- usuario_id
- tax_year
- total_dividends_brl
- total_interest_brl
- total_bond_coupons_brl
- total_capital_gains_brl
- total_capital_losses_brl
- prior_loss_carryforward_brl
- losses_used_brl
- taxable_base_brl
- calculated_tax_brl
- foreign_tax_paid_brl
- foreign_tax_credit_used_brl
- estimated_tax_due_brl
- calculation_version
- calculated_at

Pseudo-regra:

financial_income =
dividends +
interest +
bond_coupons

net_capital_result =
capital_gains -
capital_losses

taxable_result =
financial_income +
net_capital_result -
eligible_prior_losses

taxable_base =
max(0, taxable_result)

calculated_tax =
taxable_base × annual_rate

estimated_tax_due =
max(
    0,
    calculated_tax - usable_foreign_tax_credit
)

Importante:

O cálculo final deve ser produzido pelo TaxRuleEngine e não por fórmula fixa espalhada pelo frontend.

---

# 19. Controle de prejuízos

Criar:

LossCarryforward

Campos:

- usuario_id
- origin_year
- original_loss_brl
- used_brl
- remaining_brl
- last_used_year
- status

O sistema deve impedir utilização superior ao prejuízo disponível.

Relatório deve demonstrar:

Saldo inicial  
+ prejuízos do ano  
− compensações utilizadas  
= saldo final

---

# 20. Caixa

Criar ledger de caixa por corretora e moeda.

CashLedger

Cada evento deverá movimentar automaticamente o caixa.

Exemplos:

FX_IN:
+ USD

BUY:
- USD

SELL:
+ USD

DIVIDEND:
+ USD líquido

INTEREST:
+ USD líquido

FEE:
- USD

FX_OUT:
- USD

O sistema deve calcular saldo esperado e comparar com os extratos da corretora.

---

# 21. Saldo em 31/12

Entidade:

CashSnapshot

Campos:

- usuario_id
- broker_account_id
- reference_date
- balance_usd
- ptax_rate
- balance_brl
- source

reference_date normalmente:

31/12/YYYY

balance_brl =
balance_usd × applicable_ptax

Separar:

saldo patrimonial

de

resultado tributável por variação cambial.

Para conta não remunerada, a aplicação deverá aplicar a regra específica configurada para caixa.

---

# 22. Posição em 31/12

Criar snapshots anuais:

PositionSnapshot

Campos:

- tax_year
- asset_id
- quantity
- total_cost_brl
- average_cost_brl
- total_cost_usd
- market_value_usd opcional
- market_value_brl opcional

Para DIRPF, utilizar principalmente:

quantity  
total_cost_brl

Nunca substituir o custo de aquisição pelo valor de mercado.

---

# 23. PTAX

Criar módulo:

PtaxService

Responsabilidades:

- consultar Banco Central;
- armazenar cotações;
- não repetir chamadas desnecessárias;
- permitir consulta histórica;
- guardar fonte;
- guardar data solicitada;
- guardar data efetivamente utilizada;
- distinguir compra/venda se necessário;
- permitir correção manual auditável.

Tabela:

PtaxRate

- id
- requested_date
- effective_date
- quote_type
- rate
- source
- fetched_at
- manually_overridden
- override_reason

O sistema deve lidar corretamente com:

- sábados;
- domingos;
- feriados;
- dias sem publicação de PTAX.

A política de fallback deve ser configurável de acordo com a regra fiscal do exercício.

Não assumir silenciosamente uma cotação diferente da solicitada.

---

# 24. Importação de documentos

Criar módulo de importação.

Formato inicial:

- CSV Avenue;
- PDF Avenue.

Arquitetura:

ImportJob

- id
- usuario_id
- broker_account_id
- filename
- file_hash
- source_type
- status
- imported_at
- parser_version

status:

- UPLOADED
- PROCESSING
- NEEDS_REVIEW
- COMPLETED
- FAILED

Pipeline:

UPLOAD
→ identificação do documento
→ parser
→ normalização
→ validação
→ detecção de duplicidades
→ preview
→ confirmação
→ gravação dos eventos

Nunca inserir automaticamente dados ambíguos sem apresentar revisão ao usuário.

---

# 25. Prevenção de duplicidades

Cada operação importada deverá ter fingerprint.

Exemplo:

hash(
broker +
account +
event_type +
trade_date +
ticker +
quantity +
gross_value +
external_reference
)

Se possível utilizar primeiro:

external_reference / order_id.

Operações suspeitas de duplicidade devem ser apresentadas para revisão.

---

# 26. Upload de PDF Avenue

O parser deverá identificar, quando disponíveis:

- identificação da conta;
- saldos;
- posições;
- compras;
- vendas;
- dividendos;
- juros;
- retenções;
- taxas;
- datas;
- tickers;
- valores em USD.

O sistema deve preservar o documento original para auditoria.

Cada evento importado deverá apontar para:

imported_file_id

e, quando possível:

source_page  
source_section

---

# 27. Reconciliação

Criar módulo:

ReconciliationEngine

Deve comparar:

posição calculada pelo sistema

vs.

posição informada pela corretora.

E:

saldo calculado do caixa

vs.

saldo informado pela corretora.

Exibir divergências.

Exemplo:

AAPL

Calculado:
15 ações

Informe:
14 ações

Status:
DIVERGÊNCIA

Não permitir fechamento silencioso do ano quando houver divergências materiais.

---

# 28. Dashboard

Dashboard principal deve apresentar:

### Patrimônio

- custo fiscal total;
- quantidade de ativos;
- saldo de caixa;
- número de corretoras.

### Ano fiscal

- dividendos;
- juros;
- ganhos realizados;
- prejuízos realizados;
- prejuízos acumulados;
- imposto estrangeiro;
- crédito aproveitável;
- estimativa de imposto brasileiro.

### Qualidade dos dados

- operações sem PTAX;
- operações duplicadas;
- divergências;
- documentos pendentes;
- eventos não classificados.

---

# 29. Tela por ativo

Exemplo:

AAPL — Apple Inc.

Mostrar:

- quantidade atual;
- custo total BRL;
- custo médio BRL;
- custo médio USD;
- compras;
- vendas;
- dividendos;
- ganho/prejuízo realizado;
- posição em cada 31/12.

Criar timeline de eventos.

---

# 30. Simulador de venda

Usuário informa:

ticker  
quantidade  
preço USD hipotético  
data ou PTAX hipotética

O sistema retorna:

valor bruto USD  
valor estimado BRL  
custo fiscal baixado  
ganho/prejuízo BRL  
impacto estimado sobre a apuração anual

O simulador NÃO deve gravar operações reais.

---

# 31. Relatório anual

Gerar dois relatórios.

## Relatório resumido — DIRPF

Por ativo:

- ticker;
- descrição;
- corretora;
- país;
- quantidade anterior;
- quantidade atual;
- custo em 31/12 anterior;
- custo em 31/12 atual;
- rendimentos;
- imposto pago no exterior;
- resultado das alienações;
- texto sugerido de discriminação.

## Relatório detalhado — memória de cálculo

Mostrar:

- todos os eventos;
- valores USD;
- PTAX;
- valores BRL;
- fórmulas;
- custo médio antes/depois;
- ganhos/prejuízos;
- retenções;
- compensações;
- fontes.

---

# 32. Texto sugerido para Bens e Direitos

O sistema poderá gerar texto automaticamente.

Exemplo:

“15 ações de Apple Inc. (AAPL), custodiadas junto à Avenue Securities LLC, Estados Unidos. Quantidade em 31/12/2026: 15 ações. Custo histórico total de aquisição: R$ XX.XXX,XX.”

O texto deve ser editável pelo usuário antes da exportação.

---

# 33. Exportações

Suportar:

- PDF
- CSV
- XLSX
- JSON

Criar também exportação estruturada para integração futura com contadores.

---

# 34. Auditoria

Toda operação deve possuir trilha de auditoria.

AuditLog:

- id
- usuario_id
- entity
- entity_id
- action
- old_value
- new_value
- timestamp
- source

Ações:

CREATE  
UPDATE  
DELETE/SOFT_DELETE  
IMPORT  
PTAX_OVERRIDE  
RECALCULATE  
CLOSE_YEAR

O sistema deve ser capaz de explicar qualquer número apresentado.

---

# 35. Motor de cálculo

Separar completamente:

UI

de

Tax Calculation Engine.

Estrutura recomendada:

domain/
    assets/
    transactions/
    positions/
    cash/
    fx/
    taxation/
    reports/

Dentro de taxation:

TaxRuleEngine  
CapitalGainEngine  
AverageCostEngine  
ForeignTaxCreditEngine  
LossCarryforwardEngine  
AnnualClosingEngine

Os cálculos devem ser determinísticos.

Mesmas entradas + mesma versão das regras = mesmo resultado.

---

# 36. Versionamento dos cálculos

Cada fechamento precisa registrar:

calculation_version

Exemplo:

BR_FOREIGN_INVESTMENTS_2026_V1

Se uma regra for corrigida posteriormente, resultados anteriores devem continuar reproduzíveis.

---

# 37. Precisão numérica

Obrigatório utilizar tipo Decimal.

Sugestão:

valores monetários:
DECIMAL(20,8)

quantidades:
DECIMAL(24,10)

PTAX:
DECIMAL(12,8)

Somente arredondar valores para apresentação.

Durante os cálculos internos preservar precisão completa.

---

# 38. Validações importantes

O sistema deve detectar:

- compra sem PTAX;
- venda sem PTAX;
- rendimento sem PTAX;
- venda maior que a posição;
- imposto retido maior que rendimento bruto;
- líquido incompatível com bruto menos imposto;
- saldo negativo de caixa;
- duplicidade de operação;
- data fiscal inconsistente;
- ticker inexistente;
- posição calculada diferente do informe;
- saldo calculado diferente do extrato.

---

# 39. Segurança

Como o sistema armazenará CPF e informações financeiras:

- criptografia em trânsito;
- criptografia de dados sensíveis;
- autenticação segura;
- isolamento de dados por usuário;
- logs de acesso;
- backups;
- política de retenção;
- proteção contra IDOR;
- rate limiting;
- proteção CSRF/XSS/SQL injection;
- nenhuma credencial da corretora em texto puro.

Documentos enviados devem ser privados.

---

# 40. Stack sugerida

A ferramenta de vibe coding pode escolher tecnologias equivalentes.

Sugestão:

Frontend:

Next.js  
React  
TypeScript  
Tailwind  
shadcn/ui

Backend:

Next.js Server Actions/API ou Node/NestJS

Banco:

PostgreSQL

ORM:

Prisma

Autenticação:

Supabase Auth, Clerk ou Auth.js

Storage:

S3 / Supabase Storage

Jobs:

fila assíncrona para importação de documentos

Banco e regras tributárias não devem ficar exclusivamente no frontend.

---

# 41. Arquitetura de banco simplificada

Tabelas principais:

users

tax_years

broker_accounts

assets

financial_events

fx_transfers

trade_events

income_events

cash_ledger

asset_positions

position_snapshots

cash_snapshots

ptax_rates

annual_tax_calculations

loss_carryforwards

imported_files

import_jobs

reconciliation_results

tax_rules

audit_logs

---

# 42. Fluxo principal do usuário

## Primeiro acesso

1. Criar conta.
2. Escolher ano-calendário.
3. Cadastrar corretora.
4. Informar conta.
5. Fazer upload do informe ou CSV.

## Importação

1. Sistema interpreta documento.
2. Identifica operações.
3. Busca PTAX.
4. Apresenta preview.
5. Usuário confirma.
6. Sistema grava eventos.
7. Calcula posições.
8. Executa reconciliação.

## Fechamento fiscal

1. Validar operações.
2. Validar PTAX.
3. Reconciliar posições.
4. Calcular custo médio.
5. Calcular vendas.
6. Calcular rendimentos.
7. Aplicar prejuízos.
8. Calcular crédito externo.
9. Gerar apuração anual.
10. Gerar relatório DIRPF.

---

# 43. Critérios de aceite do MVP

O MVP estará funcional quando conseguir executar corretamente o seguinte cenário:

1. Usuário registra aporte BRL → USD.
2. Compra 10 AAPL.
3. Compra mais 5 AAPL em outra data.
4. Sistema calcula custo médio corretamente.
5. Usuário vende 8 AAPL.
6. Sistema calcula custo baixado e ganho/prejuízo.
7. Usuário recebe dividendos.
8. Sistema registra bruto, imposto americano e líquido.
9. Sistema consulta PTAX das operações.
10. Sistema mantém 7 ações como posição residual.
11. Sistema calcula custo residual.
12. Sistema calcula saldo de caixa.
13. Sistema cria posição em 31/12.
14. Sistema consolida resultados do exercício.
15. Sistema aplica regra tributária correspondente ao ano.
16. Sistema calcula crédito estrangeiro permitido.
17. Sistema gera memória de cálculo.
18. Sistema gera relatório resumido para DIRPF.
19. Todos os números podem ser rastreados até a operação original.

---

# 44. Testes automatizados obrigatórios

Criar testes unitários para:

- custo médio;
- compra;
- venda parcial;
- venda total;
- ganho;
- prejuízo;
- dividendos;
- imposto estrangeiro;
- crédito limitado;
- múltiplas compras;
- múltiplas vendas;
- saldo de caixa;
- posição de 31/12;
- prejuízo acumulado;
- PTAX de dia sem cotação;
- arredondamento;
- importação duplicada.

Criar também testes de regressão por ano fiscal.

Exemplo:

fixtures/tax/2024  
fixtures/tax/2025  
fixtures/tax/2026

---

# 45. Fora do escopo do MVP

Não implementar inicialmente:

- transmissão automática para Receita Federal;
- geração automática do arquivo oficial da DIRPF;
- autenticação direta na Avenue;
- opções;
- futuros;
- short selling;
- margem;
- criptomoedas;
- trust;
- empresas controladas no exterior;
- estruturas offshore complexas;
- espólio;
- tributação sucessória;
- CBE automática.

Esses recursos podem ser adicionados posteriormente.

---

# 46. Evoluções futuras

Fase 2:

- USD → BRL;
- juros sobre caixa;
- taxas;
- stock split;
- reverse split;
- spin-off;
- fusões;
- aquisição;
- troca de ticker;
- transferências entre corretoras.

Fase 3:

- multi-corretora;
- Charles Schwab;
- Interactive Brokers;
- Nomad;
- Stake;
- outras.

Fase 4:

- integração com Open Finance;
- integração com contadores;
- importação de múltiplos anos;
- comparação automática com informe oficial;
- CBE;
- assistente de preenchimento da DIRPF.

---

# 47. Regra fundamental de produto

O aplicativo é uma ferramenta auxiliar de apuração fiscal.

Nunca apresentar um número fiscal sem disponibilizar a memória do cálculo.

Para cada resultado deve ser possível responder:

- de quais operações veio;
- qual PTAX foi usada;
- qual regra tributária foi usada;
- qual versão da regra foi usada;
- quais prejuízos foram compensados;
- qual imposto estrangeiro foi considerado.

---

# 48. Aviso legal

Mostrar em área visível:

“Esta ferramenta produz cálculos e relatórios auxiliares com base nos dados fornecidos pelo usuário e nas regras tributárias configuradas para o respectivo exercício. Não substitui contador, advogado tributarista, orientação oficial da Receita Federal ou o programa oficial da DIRPF.”

---

# 49. Diretriz técnica mais importante

Não desenvolver o sistema como uma simples calculadora.

Desenvolver como um LEDGER FINANCEIRO FISCAL AUDITÁVEL.

A sequência correta é:

DOCUMENTO ORIGINAL
→ EVENTO FINANCEIRO
→ PTAX
→ LEDGER
→ POSIÇÃO
→ REGRA TRIBUTÁRIA VERSIONADA
→ CÁLCULO
→ MEMÓRIA DE CÁLCULO
→ RELATÓRIO DIRPF

Essa arquitetura é essencial para que o produto possa evoluir para múltiplos anos, múltiplas corretoras e mudanças futuras na legislação brasileira.