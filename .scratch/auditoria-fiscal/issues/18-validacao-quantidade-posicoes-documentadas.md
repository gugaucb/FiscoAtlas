# 18: Validação de posições documentadas no formulário

**What to build:** o formulário de saldo documental rejeita, na fronteira, quantidade não numérica (`AAPL, abc`), negativa e ticker duplicado — com mensagem de erro por linha — e grava a quantidade como Decimal em `positions` (mesma fonte que a reconciliação consome). Hoje o formulário só confere se há texto após a vírgula: `AAPL, abc` é gravado e o fechamento quebra com `InvalidOperation` em `Decimal(str(p["quantity"]))` na reconciliação.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [x] Formulário rejeita quantidade inválida (não numérica), negativa e ticker duplicado, com mensagem de erro por linha
- [x] Quantidade validada como Decimal na fronteira (formulário); gravada como string numérica em `positions` (JSONField) — consumível pela reconciliação sem `InvalidOperation`
- [x] Regressão: `AAPL, abc` no formulário → erro de validação, não `InvalidOperation` no fechamento (falha no código atual)