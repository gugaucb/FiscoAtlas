# 22: Matriz adversarial — teste real de 30% e fato gerador atravessando o ano (P2)

**What to build:** a matriz adversarial exercita os cenários que promete: o teste "retenção 30%" usa retenção REAL de 30% (US$ 300 sobre US$ 1.000) capturando o teto de 15% por rendimento (o atual usa US$ 30 sobre US$ 1.000 = 3% e não exercita a captura); e há cenário específico de fato gerador em 31/12 com liquidação/entrada em 02/01 do ano seguinte, provando qual data governa cada natureza (ganhos por trade_date; rendimentos pela data de recebimento — slice estreito).

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [x] Teste 05 da matriz usa retenção real de 30% (US$ 300 sobre US$ 1.000) e verifica o crédito limitado ao teto de 15%
- [x] Cenário trade_date=31/12 / settle_date=02/01 com valores esperados explícitos por natureza (ganho vs. rendimento)