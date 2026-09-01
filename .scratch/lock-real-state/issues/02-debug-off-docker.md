# 02: DEBUG off no Docker

**What to build:** DEBUG passa a vir da env DJANGO_DEBUG (default preserva o comportamento local atual); o compose define DJANGO_DEBUG=False, então erros mostram a página padrão do Django, sem expor settings, caminhos ou tracebacks.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [ ] DEBUG = env DJANGO_DEBUG (default "True" — comportamento local inalterado)
- [ ] compose.yaml define DJANGO_DEBUG=False
- [ ] .env.example documenta DJANGO_DEBUG
- [ ] Unit: settings reload reflete a env (padrão dos testes de caminhos)
