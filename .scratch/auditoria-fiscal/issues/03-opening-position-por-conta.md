# 03: OpeningPosition por conta — posição e memória de cálculo por account + asset

**What to build:** Posição de abertura passa a ser estritamente por conta: com duas
corretoras segurando o mesmo ativo (ex.: Avenue 100 AAPL custo R$ 50.000; Schwab 50
AAPL custo R$ 40.000), a posição e a memória de cálculo de cada conta refletem apenas
os seus dados — nunca a soma entre contas. O modelo recebe constraint de unicidade
(conta + ativo + data), `account` deixa de ser opcional, e a migração de dados antigos
não adivinha: 1 conta possível → atribui automaticamente; 2+ contas possíveis →
pendência de reconciliação. Custo em USD da abertura passa a ser opcional: sem o valor
histórico, o custo médio USD fica desconhecido (nunca zero inventado).

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Posição calculada respeita a conta do query (teste adversarial: 2 contas, mesmo ativo, posições e custos independentes — falha no código atual)
- [ ] Memória de cálculo fiscal gerada por conta + ativo (não ignora a conta)
- [ ] Constraint de unicidade (account, asset, reference_date) aplicada via migration
- [ ] `account` não-nulo na abertura; migração segura (1 conta → auto; 2+ → pendência de reconciliação)
- [ ] Custo USD desconhecido na abertura → custo médio USD = None (nunca 0)
- [ ] Consulta de abertura com critério temporal explícito (data mais recente ≤ data de referência)
- [ ] Princípio da regra de ouro respeitado (ver README do tracker)
