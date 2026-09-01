# 01: Bug — após informar PTAX de 31/12, o Relatório não abre (Docker, primeira execução)

**What to build:** Em banco novo (Docker), o fluxo completo funciona: informar a PTAX de fechamento na aba Relatório → o relatório renderiza com a taxa. Causa raiz: o erro "Sem TaxRule confirmada para o ano 2026" mascara a PTAX gravada — o seed cria as regras desconfirmadas e não roda no container. Correção: regras 2024–2026 (V2, Lei 14.754/2023, conforme ADR-0003) semeadas já confirmadas em banco novo (idempotente), sem tela extra de confirmação.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [ ] Unit reproduzindo o cenário exato: banco sem regras → informar PTAX pelo form → relatório abre com a taxa
- [ ] Seed idempotente cria regras 2024–2026 V2 já confirmadas em banco novo (não duplica, não reconfirma silenciosamente outras versões)
- [ ] Entrypoint Docker roda o seed em banco novo
- [ ] E2E/fluxo real Docker: informar PTAX → relatório renderiza
