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
- **Fechamento do ano** com snapshot e arrasto de prejuízos — e **reabertura
  formal** pela aplicação (devolve compensações ao saldo); anos fechados não
  aceitam alteração retroativa de eventos, PTAX, posição de abertura ou
  titularidade sem reabertura explícita
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

## Executando com Docker

### Pré-requisitos

- Docker
- Docker Compose

### Primeira execução

```bash
cp .env.example .env   # defina APP_PORT e SECRET_KEY
docker compose up -d --build
```

A aplicação sobe travada em `http://localhost:8000` (ou a porta em `APP_PORT`).
Configure a senha em `/configurar/` e desbloqueie em `/bloqueado/`.

### Ver logs

```bash
docker compose logs -f app
```

### Parar

```bash
docker compose down
```

### Reconstruir

```bash
docker compose up -d --build
```

### Ver status

```bash
docker compose ps
```

### Reiniciar

```bash
docker compose restart app
```

### Persistência

Os dados ficam no volume Docker `app_data`, montado em `/data` no container:

- `/data/db.sqlite3` — banco principal (cifrado com SQLCipher)
- `/data/vault.sqlite3` — chaves encapsuladas e log de auditoria
- `/data/documents/` — documentos anexos cifrados

Nem `docker compose down` nem `up -d --build` apagam esses dados.

### Backup

Sempre com a aplicação parada (evita copiar o SQLite aberto/inconsistente):

```bash
docker compose stop app
docker run --rm -v fiscoatlas_app_data:/data -v "$PWD:/backup" python:3.11-slim-bookworm \
    tar czf /backup/backup-fiscoatlas.tgz /data
docker compose start app
```

### Restaurar

```bash
docker compose down
docker run --rm -v fiscoatlas_app_data:/data -v "$PWD:/backup" python:3.11-slim-bookworm \
    sh -c "rm -rf /data/* && tar xzf /backup/backup-fiscoatlas.tgz -C /"
docker compose up -d
```

Alternativa dentro da aplicação (com ela desbloqueada): comando
`backup_encrypted` / tela de documentos — produz um zip cifrado.

## Licença

GPL-3.0 — veja [LICENSE](LICENSE).
