# 01: App security + CryptoProvider (AES-256-GCM)

**What to build:** Base criptográfica do sistema: um provedor de criptografia que
qualquer parte do sistema pode usar para cifrar/decifrar bytes e "embrulhar"
chaves, sempre com AES-256-GCM autenticado e nonce único, com versão de algoritmo
registrada no resultado para migração futura. É prefatoração: não tem UI.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] App `security` criado e registrado
- [ ] Provedor com encrypt/decrypt/generateKey/wrapKey/unwrapKey
- [ ] AES-256-GCM com nonce único por operação; mesma entrada gera ciphertexts diferentes
- [ ] Ciphertext adulterado falha na autenticação (tag)
- [ ] `crypto_version` incluído no formato cifrado
- [ ] Testes: roundtrip, nonce distinto, tampering falha
