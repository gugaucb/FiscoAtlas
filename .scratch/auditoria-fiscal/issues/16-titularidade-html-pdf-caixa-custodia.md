# 16: Titularidade nos campos fiscais do HTML e do PDF (caixa, custódia e isenção)

**What to build:** em conta conjunta (ex. 50%), o relatório auxiliar destinado à declaração — HTML e PDF — apresenta a fatia do contribuinte nos campos fiscais: "Valor para declaração" do caixa, "Custo fiscal BRL" e "Situação 31/12" da custódia, e a isenção de variação cambial de caixa não remunerado (seção 7). Os valores integrais da conta permanecem apenas como informação auxiliar claramente rotulada. O PDF hoje usa os integrais nos campos de declaração (saldo, custo e situações) e a isenção é calculada sobre a conta inteira.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [x] HTML e PDF: caixa exibe a fatia do contribuinte como "Valor para declaração"; integral fica rotulado como auxiliar
- [x] PDF: custódia usa as fatias do contribuinte em "Custo fiscal BRL" e "Situação 31/12"; integral como referência auxiliar
- [x] Seção 7 (isenção): isenção atribuída pela fatia do contribuinte
- [x] Regressão com conta conjunta 50% que falha no código atual (valores integrais nos campos fiscais)
