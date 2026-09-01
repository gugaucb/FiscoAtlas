# FiscoAtlas

Apuração de IRPF para investimentos no exterior (Lei 14.754/2023) — aplicação
Django single-user, local-first, com banco cifrado (SQLCipher) e documentos
anexos cifrados.

## Funcionalidades

- **Lançamentos**: aportes, retiradas, compras, vendas, dividendos, juros,
  taxas e impostos retidos, com PTAX automática (BCB) ou manual (com motivo)
- **Posições e custo médio** em USD e BRL (método da média)
- **Caixa** por corretora com histórico
- **Apuração anual**: renda, ganhos, prejuízos compensáveis, crédito de
  imposto pago no exterior (limitado a 15% por rendimento)
- **Relatório DIRPF** (HTML + PDF) e **memória de cálculo** linha a linha (PDF)
- **Fechamento do ano** com snapshot e arrasto de prejuízos
- **Segurança**: senha + recovery key, auto-lock, banco SQLCipher, documentos
  cifrados, log de auditoria

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py runsecure
```

O servidor sobe travado; configure a senha em `/configurar/` e desbloqueie em
`/bloqueado/` pelo navegador.

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

Os testes E2E usam Playwright (`pytest tests/e2e/`).

## Licença

GPL-3.0 — veja [LICENSE](LICENSE).
