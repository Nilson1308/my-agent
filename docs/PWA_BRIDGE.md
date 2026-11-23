# Ponte PWA ↔ my-agent (Onda 3)

API read-only para um PWA complementar (ex.: `app-pwa-gf` ou futuro `work-agent`).

## Endpoint

`GET /api/pwa/snapshot/`

**Header:** `X-PWA-Token: <PWA_API_TOKEN>` (mesmo valor do `.env`)

**Resposta 200:** JSON com `shopping`, `tasks_pending`, `events_today`, `generated_at`.

**Erros:**

- `503` — `PWA_API_TOKEN` não configurado no servidor
- `401` — token ausente ou inválido

## Exemplo

```bash
curl -sS -H "X-PWA-Token: $PWA_API_TOKEN" \
  https://copa.mogidascruzes.sp.gov.br/api/pwa/snapshot/
```

## Próximo passo (work-agent)

O produto profissional em `work-agent/CONTEXT.md` reutiliza esta ideia com auth JWT e entidades `Meeting`/`ActionItem`; o my-agent permanece como backend pessoal até o split de apps.