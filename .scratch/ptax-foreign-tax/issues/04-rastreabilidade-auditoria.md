# 04: Rastreabilidade de auditoria — memória de cálculo e edição manual

**What to build:** O usuário consegue ver, conferir e corrigir pelo navegador as duas conversões de cada evento com imposto no exterior. A memória de cálculo (PDF de auditoria) discrimina para cada componente: data fiscal, tipo de cotação, cotação aplicada, valor USD e valor BRL — sem condensar rendimento e imposto num único conjunto de campos. A edição manual dos dados do imposto gera trilha de auditoria.

**Blocked by:** 03 (Cálculo fiscal e relatório separados).

**Status:** resolved

- [ ] Memória de cálculo registra separadamente: data do rendimento, data da PTAX do rendimento, tipo da cotação, taxa, valor BRL — e data do pagamento do imposto, data da PTAX do imposto, tipo (COMPRA), taxa, valor BRL
- [ ] Relatório exibe as duas conversões separadamente (dados + cotação + taxa de cada componente)
- [ ] Formulário permite informar/corrigir: `foreign_tax_payment_date`, `jurisdiction_level`, `tax_type`, `date_evidence_source` e as taxas (com motivo)
- [ ] Toda alteração nesses campos gera trilha de auditoria com old_value, new_value, changed_at e reason
- [ ] Teste de aceite: fluxo pelo navegador — registrar dividendo com retenção em data distinta, conferir as duas cotações no relatório, corrigir a data documental e ver a trilha
