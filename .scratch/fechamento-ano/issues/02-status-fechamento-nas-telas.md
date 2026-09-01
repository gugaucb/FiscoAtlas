# 02: Status de fechamento nas telas + aviso de ano anterior aberto

**What to build:** A apuração e o relatório informam se o ano está fechado. Se o ano anterior não está fechado, o relatório exibe aviso claro de que o saldo de prejuízo a compensar herdado pode estar incompleto, orientando a fechar o ano anterior antes de considerar os valores definitivos.

**Blocked by:** 01 (o conceito/fluxo de fechamento precisa existir).

**Status:** resolved

- [x] Tela de apuração exibe selo "Ano fechado em <data>" ou "Ano em aberto"
- [x] Tela de relatório exibe o mesmo selo para o ano do relatório
- [x] Se o ano anterior não está fechado, o relatório mostra aviso destacado orientando o fechamento (impacto na compensação de prejuízos)
- [x] Sem aviso quando o ano anterior está fechado ou não há movimentação relevante
- [x] Testes cobrem os dois estados e o aviso
