# CLAUDE.md

## Git workflow

- Desenvolver novas funcionalidades sempre em branch (`feat/<nome>` para features, `fix/<nome>` para correções), criada a partir de `main`.
- Fazer merge de volta em `main` após os testes passarem.
- Marcar releases com tag semântica (ex.: `v0.1.0`).

## Agent skills

### Issue tracker

Issues live as local markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Automação Playwright (capturas de tela e E2E)

- **NUNCA clique em `button[type=submit]` genérico ou `buttons[-1]`**: o form
  "Bloquear" da navbar também é submit e pode ser capturado no lugar do botão
  principal (sintoma: POST vai para `/desbloquear/` em vez do form alvo).
  Sempre usar seletor específico: `#id-do-botão` (ex.: `#save-payment`) ou
  `form[action*="<rota>"] button[type="submit"]`. No template base, o form
  principal geralmente NÃO tem `action` (posta na própria URL).
- **`<input type="date">` só aceita ISO (`yyyy-MM-dd`)**: templates
  localizados renderizam DD/MM/AAAA e o navegador bloqueia o submit
  silenciosamente por validação HTML5 (sem erro visível). Preencher com
  `page.fill(selector, "2026-03-15")` antes de submeter.
- Fechamento de ano (`confirm()` nativo): registrar `page.on("dialog",
  lambda d: d.accept())` antes do clique, senão o Playwright dispensa o
  diálogo e o form não envia.
- Banco novo para rodar local: `migrate` + **`migrate --database=vault`**
  (o alias vault não é coberto pelo migrate default) + `seed_tax_rules`.
- Fechamento de ano exige: saldos documentais (`/documentar-saldos/`,
  caixa conferindo com o ledger — dividendo entra LÍQUIDO no caixa) e
  imposto exterior totalmente classificado (`recoverability_status`).

### Domain docs

Single-context layout: one `CONTEXT.md` + `docs/adr/` at repo root. See `docs/agents/domain.md`.
