# ADR-0002: Aplicação single-user, local-first

Data: 2026-08-30
Status: Aceito

## Contexto

O sistema é uma ferramenta fiscal auxiliar de uso pessoal do dono do projeto: um único investidor com conta na Avenue. O spec original (seções 5 e 39) previa multiusuário com segregação completa, LGPD, rate limiting, proteção IDOR etc.

## Decisão

Simplificar para **usuário único**: autenticação simples via Django AllAuth (proteção local), sem multi-tenancy — `usuario_id` não aparece no modelo. Deploy local via Docker, com backup `pg_dump` diário para pasta sincronizada em nuvem.

## Consequências

- Removidas do MVP: cadastro público, segregação por usuário, IDOR/rate limiting, criptografia multi-inquilino.
- Dado fiscal fica no Docker local; o backup diário mitiga perda.
- Se o projeto virar produto, haverá refatoração para reintroduzir `usuario_id` — aceito conscientemente como trade-off de escopo do MVP.
- Alternativa rejeitada: manter multi-tenancy "para o futuro" — custo imediato de segurança/infra sem uso real.
