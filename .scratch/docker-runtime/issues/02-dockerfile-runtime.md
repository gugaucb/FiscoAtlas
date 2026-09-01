# 02: Dockerfile runtime seguro

**What to build:** Imagem multi-stage (deps → runtime) da aplicação com a dependência nativa SQLCipher funcionando, sem ferramentas de dev, sem dados do usuário, executando como usuário não-root.

**Blocked by:** 01 (caminhos-env).

**Status:** resolved

- [ ] Multi-stage: stage de dependências compila sqlcipher3; stage runtime só runtime (libsqlcipher compartilhada + requirements.txt, sem requirements-dev)
- [ ] Usuário não-root com posse dos diretórios graváveis (/data e subpastas)
- [ ] Imagem não contém .env, banco, vault, documents/ nem backups (verificável)
- [ ] .dockerignore endurecido (.git, .venv, dados do usuário, compose, Dockerfile, backups, tests)
- [ ] `docker build` conclui e o entrypoint padrão é `runsecure`
