# 15: Crédito exterior limitado ao IR devido (potencial × utilizado × não aproveitado)

**What to build:** o crédito de imposto exterior aproveitado não pode exceder o IR brasileiro devido após a compensação de prejuízos. O engine distingue quatro parcelas: elegível, potencial (limite de 15% por rendimento), efetivamente utilizado (limitado globalmente ao IR devido) e não aproveitado — todas visíveis no relatório, nada descartado silenciosamente.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Invariante `credit_used_total <= tax_brl` garantida pelo engine
- [ ] Output expõe potencial, utilizado e não aproveitado (além de elegível/ineligível já existentes)
- [ ] Relatório e PDF exibem a distinção; snapshot registra o utilizado real
- [ ] Regressão: bruto 1.000, retenção 150, prejuízos 900 → tax 15, used 15, unused 135 (falha no código atual)