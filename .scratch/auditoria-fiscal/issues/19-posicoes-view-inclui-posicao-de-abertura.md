# 19: `/posicoes/` inclui contas e ativos descobertos por posição de abertura

**What to build:** a tela de posições descobre contas e ativos pela MESMA fonte que o relatório e a reconciliação — união de eventos ativos e posições de abertura. Hoje descobre só por `FinancialEvent`: carteira carregada exclusivamente por `OpeningPosition` existe fiscalmente (relatório, CBE, reconciliação) mas não aparece em `/posicoes/`.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [x] `/posicoes/` lista posições de contas/ativos existentes apenas por `OpeningPosition` (mesma fonte de descoberta do relatório e da reconciliação)
- [x] Regressão: `OpeningPosition` 100 AAPL sem eventos → linha aparece em `/posicoes/` (falha no código atual)