# Ponte PWA ↔ my-agent (Onda 3)

PWA em **`/app/`** (código em `my-agent/pwa/`). API read-only; `work-agent` reusará o padrão com JWT.

## Endpoint

`GET /api/pwa/snapshot/`

**Header:** `X-PWA-Token: <PWA_API_TOKEN>` (mesmo valor do `.env`)

**Resposta 200:** JSON com `shopping`, `tasks_pending`, `events_today`, `generated_at`.

**Escrita (PWA v1):**

- `PATCH /api/pwa/shopping/{id}/` — body `{"bought": true}` (marca comprado)
- `PATCH /api/pwa/tasks/{id}/` — conclui tarefa pendente
- `PATCH /api/pwa/shopping/{id}/` — `{"bought": false}` desfaz compra
- `PATCH /api/pwa/events/{id}/` — `{"dismissed": true}` remove compromisso
- Snapshot inclui `shopping.bought_recent` (7 dias)
- `POST /api/pwa/shopping/` — `{"name", "quantity"?}`
- `POST /api/pwa/tasks/` — `{"title", "context"?}`
- `PATCH /api/pwa/tasks/{id}/` — `{"status": "pending"}` reabre; `"done"` conclui
- Snapshot: `tasks_done_recent`

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