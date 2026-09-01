# ADR-0001: Regras tributárias como dados versionados, não código

Data: 2026-08-30
Status: Aceito

## Contexto

Legislação fiscal brasileira muda por ano-calendário (Lei 14.754/2023 e sucessoras): alíquotas, faixas, tratamento de caixa não remunerado, limites de crédito estrangeiro. Codificar a alíquota de 15% (ou qualquer faixa) em pontos da aplicação tornaria cada mudança legal uma refatoração e impossibilitaria reproduzir cálculos de anos passados.

## Decisão

Toda regra tributária é um **dado** (TaxRule) versionado por ano-calendário e por `rule_version`, armazenado no banco, com `effective_from`/`effective_until`. Os motores de cálculo (TaxRuleEngine, ForeignTaxCreditEngine, etc.) são genéricos e recebem a regra como parâmetro. Valores default (tabela progressiva 14.754/2023, PTAX venda) ficam marcados como "a confirmar com contador" até validação — corrigi-los é editar dados, não código.

## Consequências

- Mesmas entradas + mesma versão de regra = mesmo resultado (determinismo e reprodução de fechamentos passados).
- Correção legislativa = carga de novos dados, zero deploy de lógica.
- Custo: mais uma tabela e versionamento explícito desde o primeiro dia.
- Alternativa rejeitada: constantes no código — simples no início, insustentável no ano 2.
