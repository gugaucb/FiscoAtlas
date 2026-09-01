# 01: Botão "Fechar ano" na apuração

**What to build:** Na tela de apuração de um ano, o usuário clica em "Fechar ano" e o sistema salva o snapshot de fechamento (`AnnualAssessment`) daquele ano, mostrando confirmação com os valores consolidados (imposto devido, prejuízo a compensar). Fechar de novo recalcula e atualiza o snapshot (nunca duplica). Com o ano anterior fechado, o ano seguinte já herda o saldo de prejuízo — comportamento do motor já implementado.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] Botão "Fechar ano {{ano}}" na tela de apuração (POST, com confirmação)
- [x] Após fechar, mensagem de sucesso exibe imposto devido e prejuízo a compensar
- [x] Snapshot único por ano: fechar duas vezes atualiza, não duplica
- [x] Com snapshot de 2025 salvo, apuração de 2026 mostra prejuízo herdado (integração com o motor)
- [x] Testes cobrem fechamento, re-fechamento e herança do prejuízo no ano seguinte
