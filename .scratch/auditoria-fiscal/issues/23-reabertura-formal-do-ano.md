# 23: Congelamento/reabertura formal do ano (P0)

**What to build:** caminho formal e trilhado para reabrir um ano fechado: a reabertura só é possível se nenhum ano posterior estiver fechado (evita desfazer consumos de prejuízo em cascata), exige confirmação do usuário, apaga o snapshot do ano e reabre os anos posteriores à reavaliação. Hoje não há caminho pela aplicação — reabrir exigiria SQL manual, e o ano anterior reaberto não é detectado como tal (o relatório avisa `prev_closed` pelo snapshot; a reabertura formal integra-se a isso).

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [x] Ação de reabrir ano na apuração: bloqueada se algum ano posterior tem snapshot; com confirmação e mensagem na trilha
- [x] Ano reaberto: relatório do ano seguinte volta a exibir o aviso de "ano anterior não fechado" (via `prev_closed`, que volta a ser False)
- [x] Regressão: reabrir 2025 com 2026 fechado → bloqueio; sem 2026 fechado → reabre e desaparece o snapshot (falha no código atual — não havia reabertura)