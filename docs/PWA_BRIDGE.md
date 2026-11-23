# Ponte PWA ↔ my-agent (Onda 3)

PWA em **`/app/`** (código em `my-agent/pwa/`). Leitura + escrita tátil; `work-agent` ver `docs/WORK_AGENT.md`.

## Endpoint

`GET /api/pwa/snapshot/`

**Observabilidade (4.9):** `GET /api/pwa/observability/?days=7` — métricas PWA vs Telegram (mesmo header de token).

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
- Snooze: `POST /api/pwa/events/{id}/snooze/`

**Web Push (4.6):**

- `GET /api/pwa/push/vapid/` — `public_key`, `enabled` (sem auth)
- `POST /api/pwa/push/subscribe/` — body Web Push `endpoint` + `keys`
- `POST /api/pwa/push/unsubscribe/`

**Chat agente (5.1–5.2):**

- `POST /api/pwa/chat/` — `{"text": "..."}` — mesma IA do Telegram (`run_agent_message`); log `channel=pwa`
- `POST /api/pwa/chat/audio/` — multipart campo `audio` → Whisper

**Documentos (5.4–5.5):**

- `POST /api/pwa/documents/pdf/` — multipart `file`, form `context`
- `POST /api/pwa/documents/image/` — foto → OCR/descrição (Groq vision) → notas

**Geofence / mapa (5.3):**

- Webhook body: `location`, opcional `lat`, `lon`
- `GET /api/pwa/geofence/events/?limit=40`

**Pairing / rotação (4.7):**

- Auth aceita `PWA_API_TOKEN` ou `PWA_API_TOKEN_PREVIOUS`
- `POST /api/pwa/pairing/create/` (com token) → `pair_url`, `code`, `expires_in`
- `POST /api/pwa/pairing/exchange/` — `{"code"}` → `{"token"}` (uso único, Redis)

**Erros:**

- `503` — `PWA_API_TOKEN` não configurado no servidor
- `401` — token ausente ou inválido

## Exemplo

```bash
curl -sS -H "X-PWA-Token: $PWA_API_TOKEN" \
  https://copa.mogidascruzes.sp.gov.br/api/pwa/snapshot/
```

## work-agent

Ver `docs/WORK_AGENT.md` e `work-agent/CONTEXT.md` (JWT, DB isolado).