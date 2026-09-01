# 04: SQLCipher no banco + migração do banco atual

**What to build:** O arquivo do banco fica criptografado em repouso, protegido pela
VaultKey: abri-lo com sqlite3/DB Browser sem a chave revela apenas bytes ilegíveis
(sem schema, sem registros). O banco existente é migrado uma única vez para o
formato cifrado. Plano B (se o driver sqlcipher3 não compilar): cifrar o arquivo
do banco fora do SQLite com AES-256-GCM, decisão documentada em ADR.

**Blocked by:** 02 (precisa da VaultKey para chavear o banco).

**Status:** resolved

- [x] Conexão SQLite do Django passando a ser aberta com chave via VaultKey
- [x] Banco aberto sem chave não revela schema nem registros (teste com sqlite3 puro)
- [x] Cópia do banco para "outra máquina" permanece ilegível sem chave
- [x] Migração one-time do db.sqlite3 atual para o formato cifrado, sem perda de dados
- [x] Suite de testes roda com chave de teste gerenciada (suite 100% green)
- [x] Plano B se driver falhar: ADR + criptografia de arquivo; testes equivalentes
- [x] Testes: senha correta abre, incorreta não abre, backup copiado exige chave
