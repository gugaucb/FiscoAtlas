# CLAUDE.md

## Git workflow

- Desenvolver novas funcionalidades sempre em branch (`feat/<nome>` para features, `fix/<nome>` para correções), criada a partir de `main`.
- Fazer merge de volta em `main` após os testes passarem.
- Marcar releases com tag semântica (ex.: `v0.1.0`).

## Agent skills

### Issue tracker

Issues live as local markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context layout: one `CONTEXT.md` + `docs/adr/` at repo root. See `docs/agents/domain.md`.
