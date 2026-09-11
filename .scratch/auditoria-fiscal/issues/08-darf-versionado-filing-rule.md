# 08: DARF versionado por exercício — FilingRule

**What to build:** As regras de arrecadação do DARF saem do código fixo (código 0211,
mínimo R$ 10, vencimento no último dia útil de abril, 8 quotas) e viram um modelo
versionado por **exercício** da declaração (ano-calendário 2026 → exercício 2027).
Para gerar a orientação definitiva de pagamento, o exercício precisa de regra
homologada — sem ela, a orientação fica PRELIMINAR com aviso, nunca um vencimento
inventado. O parcelamento respeita os mínimos (quota mínima, imposto mínimo para
parcelar, número máximo) calculando o número válido de quotas — não divisão
automática por 8. DARF abaixo do mínimo não é "imposto extinto": fica claro que é
**adiamento** — o valor se acumula ao mesmo código nos períodos subsequentes
(art. 938, § 5º, RIR/2018; referência corrigida no ticket 02).

**Blocked by:** 02 (Referências legais corretas).

**Status:** done

- [ ] Modelo FilingRule versionado por exercício (vencimento, código DARF, mínimos, máximo de quotas, base legal, homologação) — sem constantes hardcoded na geração
- [ ] Exercício sem regra homologada → orientação PRELIMINAR com aviso; nunca data inventada
- [ ] filing_year = ano-calendário + 1 resolvido corretamente
- [ ] Parcelamento respeita mínimos e máximo (testes com R$ 99 quota única, R$ 100 mínimo de quota, R$ 300 com nº válido de quotas — falha no código atual)
- [ ] DARF < R$ 10: semântica de adiamento/acúmulo explícita na mensagem e nos dados (não "dispensado" como extinção)
- [ ] Teste de regressão com valores esperados calculados explicitamente
- [ ] Princípio da regra de ouro respeitado (ver README do tracker)
