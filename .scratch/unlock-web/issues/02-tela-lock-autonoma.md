# 02: Tela de lock autônoma (sem nav)

**What to build:** A tela /bloqueado/ (lock, setup e setup_done) usa um base mínimo sem a navegação do app — sem abas que só redirecionam de volta. Após unlock, as abas funcionam normalmente.

**Blocked by:** 01 (runsecure boot travado) — para o smoke real de ponta a ponta.

**Status:** resolved

- [ ] security/templates/security/base.html mínimo, sem topbar/nav
- [ ] lock.html, setup.html, setup_done.html extendem o novo base
- [ ] Testes: /bloqueado/ (configurada e não configurada) sem nav; suite green
