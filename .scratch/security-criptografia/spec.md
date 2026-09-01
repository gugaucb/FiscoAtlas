# Spec — Segurança e criptografia (single-user, local-first)

## Problema

O sistema armazena dados altamente sensíveis (CPF, contas, operações, posições,
relatórios) em SQLite plaintext. Requisito: posse isolada do banco, backups ou
arquivos não deve permitir leitura sem a chave criptográfica.

## Diretriz

SINGLE USER + LOCAL FIRST + ENCRYPTED BY DEFAULT + ZERO PLAINTEXT AT REST.

## Decisões

- SQLite + SQLCipher (AES-256). **Plano B aprovado pelo usuário:** se o driver
  Python (sqlcipher3/pysqlcipher3) não compilar no macOS, criptografar o arquivo
  do banco fora do SQLite (AES-256-GCM via app `security`), registrado em ADR.
- Envelope encryption local: senha → Argon2id → KEK → unwrap VaultKey (256 bits
  CSPRNG) → SQLCipher / AES-256-GCM. Senha nunca é chave direta.
- Wrappers da VaultKey: password + recovery key apenas (device/Keychain/DPAPI
  ficam fora por enquanto — decisão do usuário).
- Recovery key de alta entropia, exibida só na criação/regeneração, wrappa cópia
  da VaultKey.
- Troca de senha/recuperação = rewrap da VaultKey; banco não é recriptografado.
- Login local com tela bloqueada, bloqueio manual e auto-lock configurável.
- Documentos importados: FileKey aleatória por arquivo, AES-256-GCM, temp apagado.
- Backup sempre cifrado; exportações nunca persistidas em plaintext.
- Logs sem dados sensíveis (CPF, chaves, valores); auditoria com
  `security_audit_log` e hash chaining.
- Crypto agility: `crypto_version` + abstração de provider.

## Slices

1. App `security` + CryptoProvider AES-256-GCM (base criptográfica).
2. Vault: Argon2id, VaultKey, wrappers password/recovery, troca de senha.
3. Login local + bloqueio manual + auto-lock + auditoria de segurança.
4. SQLCipher no banco + migração do banco atual (ou plano B).
5. Criptografia de documentos importados (FileKey por arquivo).
6. Backup cifrado + exportação segura + hardening de logs.
