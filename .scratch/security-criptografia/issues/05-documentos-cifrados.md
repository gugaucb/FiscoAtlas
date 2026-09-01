# 05: Criptografia de documentos importados

**What to build:** Importar PDF/CSV da Avenue (informe, extrato, operações) salva
apenas o arquivo cifrado no disco (`<hash>.enc` com FileKey própria wrappada pela
VaultKey) e a metadata cifrada em `encrypted_documents`; o original em temp é
apagado. O download descriptografa on-the-fly. Roubar a pasta de documentos não
revela nada.

**Blocked by:** 04.

**Status:** resolved

- [x] Upload de PDF/CSV é salvo cifrado (AES-256-GCM, FileKey por documento)
- [x] FileKey wrappada pela VaultKey no banco; nunca em plaintext
- [x] Metadata: nome cifrado, hash do arquivo, crypto_version
- [x] Arquivo temporário/original apagado após cifrar
- [x] Download descriptografa on-the-fly e serve o documento correto
- [x] Arquivo adulterado no disco falha na autenticação ao baixar
- [x] Testes: roundtrip cifrar/decifrar, tampering falha, sem plaintext na pasta
