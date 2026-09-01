# 01: Caminhos persistentes configuráveis por variável de ambiente

**What to build:** Os três artefatos persistentes do sistema (banco principal cifrado, vault de chaves e documentos cifrados) ficam acessíveis por variável de ambiente: `DATABASE_URL` (já suportado, testado), `VAULT_DB_PATH` (novo, default "vault.sqlite3" — comportamento atual inalterado) e `DOCUMENT_STORAGE_PATH` (já suportado, testado). Isso permite ao container apontar tudo para volumes.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [ ] `VAULT_DB_PATH` configurável via env com default atual (comportamento local inalterado)
- [ ] Unit: vault criado no caminho da env; default continua vault.sqlite3 na raiz
- [ ] Unit: `DATABASE_URL` aponta o banco principal para outro arquivo (suporte existente coberto por teste)
- [ ] Unit: `DOCUMENT_STORAGE_PATH` aponta documentos para outro diretório (suporte existente coberto por teste)
