# 04: Registros para regressão futura — valores esperados + modo de rodar

**What to build:** Documento canônico do cenário junto dos testes: tabela de datas, quantidades, preços, PTAX e valores de apuração esperados por ativo e por ano (2026 e 2027), mais as instruções de como rodar a suíte isolada. É a referência para qualquer regressão fiscal futura: qualquer mudança de comportamento fiscal precisa ou manter esses números ou atualizá-los com justificativa.

**Blocked by:** 02, 03 (valores finais só existem depois do ciclo completo e do multi-ano).

**Status:** ready-for-agent

- [ ] Cenário canônico documentado: todos os eventos com datas, quantidades, preços, retenções e PTAX manual usada
- [ ] Tabela de valores esperados por ano: rendimento bruto, perdas, base, IR devido, crédito aproveitado, saldo de caixa por conta, custo médio por ativo
- [ ] Comandos para rodar a suíte E2E isolada e a completa, documentados (pytest tests/e2e/)
- [ ] Nota explicando a regra de ouro: valores esperados explícitos; mudança de número exige justificativa fiscal no commit