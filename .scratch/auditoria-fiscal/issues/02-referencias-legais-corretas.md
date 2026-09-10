# 02: Referências legais corretas — Res. BCB nº 279/2022 e art. 938 RIR/2018

**What to build:** Todas as referências legais erradas do sistema corrigidas
globalmente — código, template, testes, mensagens de interface e manual. A CBE é
regulamentada pela **Resolução BCB nº 279/2022** (que regulamenta a Lei 14.286/2021),
não pela "Res. BCB 278/2022". A dispensa de DARF abaixo de R$ 10 (com acúmulo nos
períodos subsequentes) está no **art. 938, §§ 4º e 5º, do RIR/2018**, não no "art. 872".
Não basta mudar comentários: testes que assertam as referências erradas também mudam
(documentando por que o comportamento anterior estava errado).

**Blocked by:** None (can start immediately).

**Status:** done (branch feat/auditoria-fiscal, commit d34048c)

- [x] Nenhuma ocorrência de "278/2022" ou "Res. BCB nº 278" restante (código, template, testes, docs, manual)
- [x] Nenhuma ocorrência de "art. 872" restante (código, testes, manual) — substituída por "art. 938, §§ 4º e 5º, RIR/2018"
- [x] Mensagens de interface com as referências corrigidas
- [x] Busca global (case-insensitive) por "278/2022" e "872" zero retornos fiscais relevantes
- [x] Princípio da regra de ouro respeitado (ver README do tracker) — teste que assertava a mensagem errada substituído com documentação
