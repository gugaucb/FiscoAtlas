# 03: compose.yaml + persistência + README

**What to build:** `docker compose up -d --build` sobe a aplicação em http://localhost:8000 com banco, vault e documentos em volumes Docker que sobrevivem a `down` e a reconstrução da imagem. `docker-compose.yml` antigo (Postgres) removido. README documenta execução, backup e restauração.

**Blocked by:** 02 (Dockerfile).

**Status:** ready-for-agent

- [ ] compose.yaml: serviço app, porta 8000, restart unless-stopped, env via .env.example, healthcheck em /bloqueado/ (200 mesmo travado), usuário não-root
- [ ] Volumes: app_data:/data (banco + vault) e app_documents:/data/documents; compose de dev Postgres removido
- [ ] .env.example documentando APP_PORT, DATABASE_URL, VAULT_DB_PATH, DOCUMENT_STORAGE_PATH, SECRET_KEY (sem valores reais)
- [ ] README: seção "Executando com Docker" com subir/parar/logs/status/restart, backup (backup_encrypted) e restauração
- [ ] Validação real executada: build, up, ps, logs sem erros, aplicação abre
- [ ] Teste crítico de persistência: registro criado sobrevive a `down`+`up` e a `down`+`up --build`
- [ ] Teste de imagem: sem .env/banco/documentos/secrets dentro da imagem
