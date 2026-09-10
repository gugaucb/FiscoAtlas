# 01: Importador Schwab — mapear SELL e proibir omissão silenciosa

**What to build:** Ao importar um CSV da Schwab, nenhuma linha pode desaparecer
silenciosamente. Vendas ("Sell") passam a ser importadas como eventos SELL (fato
gerador de ganho/perda — hoje são descartadas na leitura, o que pode eliminar um fato
tributável inteiro). Qualquer ação não suportada (ex.: Transfer, ações desconhecidas)
gera uma pendência **visível e bloqueante** na prévia da importação, com número da
linha, ação original e motivo — nunca um `continue` silencioso. O usuário vê na
prévia quantas linhas foram importadas e quantas ficaram pendentes, e não consegue
concluir a importação sem reconhecer as pendências.

**Blocked by:** None (can start immediately).

**Status:** done (branch feat/auditoria-fiscal, commit ef59c72)

- [x] SELL é mapeado e importado como evento de venda (com teste de regressão que falha no código atual)
- [x] Linha com ação não suportada aparece na prévia como pendência bloqueante (linha, ação bruta, motivo) — nunca é descartada sem rastro
- [x] ImportBatch registra contagem conciliada: linhas do arquivo = importadas + pendências + ignoradas confirmadas
- [x] Prévia da importação exibe pendências ao usuário e exige reconhecimento explícito para concluir
- [x] Teste adversarial: CSV com SELL + Transfer + evento desconhecido — nada desaparece; valores esperados explícitos
- [x] Princípio da regra de ouro respeitado (ver README do tracker)
