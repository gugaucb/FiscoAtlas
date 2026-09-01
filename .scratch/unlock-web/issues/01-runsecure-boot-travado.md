# 01: runsecure sobe travado, sem senha no terminal

**What to build:** `.venv/bin/python manage.py runsecure` sobe o servidor sem pedir senha no terminal; o desbloqueio acontece pelo navegador em /bloqueado/ (senha ou recovery key), inclusive na primeira instalação (setup web).

**Blocked by:** None (can start immediately).

**Status:** resolved

- [ ] check_migrations é no-op (override válido, não apenas herança)
- [ ] handle chega ao inner_run sem chave em state e sem getpass, com use_reloader=False
- [ ] Testes existentes de runsecure atualizados; suite green
- [ ] Smoke real: servidor travado no ar; unlock web funciona
