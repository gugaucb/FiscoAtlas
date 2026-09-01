# 02: Infra Playwright + smoke de desbloqueio

**What to build:** Playwright instalado (chromium) e fixture de teste que sobe o LiveServer (mesmo processo — vault key compartilhada em memória) e um browser real. Smoke: abrir /bloqueado/, digitar a senha no navegador, chegar à home.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [ ] playwright + chromium instalados no venv; requirido como dev dependency
- [ ] Fixture browser/page + liveserver com vault configurada e desbloqueável pela UI
- [ ] Smoke E2E: lock screen → senha → home visível no browser real
- [ ] Teste roda junto da suite sem quebrar os demais (skip se playwright ausente)
