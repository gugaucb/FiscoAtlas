# 11: DIRPF PRELIMINAR sem schema homologado

**What to build:** O relatório DIRPF só se autodenomina "homologado" quando existe
um schema de relatório efetivamente homologado. Hoje, sem schema configurado, ele
retorna defaults e marca o status como HOMOLOGADO — um relatório sem base versionada
aparecendo como definitivo. Sem schema, o status vira PRELIMINAR (com aviso ao
usuário); HOMOLOGADO exige schema homologado explicitamente. A apuração matemática
continua permitida sem schema — o que muda é o rótulo e a confiança.

**Blocked by:** None (can start immediately).

**Status:** done

- [ ] Sem schema → status PRELIMINAR com aviso (falha no código atual, que retorna HOMOLOGADO)
- [ ] HOMOLOGADO somente com schema explicitamente homologado
- [ ] Interface distingue visualmente preliminar de homologado
- [ ] Apuração matemática segue funcionando sem schema
- [ ] Princípio da regra de ouro respeitado (ver README do tracker)
