# Onda 4 — PWA e API complementar

Superfície **`/app/`** evoluindo de leitora para **painel tátil** do my-agent, sem substituir o Telegram.

## 4.1 Escrita e desfazer ✅ implementado

| Item | API / UI |
|------|----------|
| Marcar comprado | `PATCH .../shopping/{id}/` `bought: true` |
| **Desfazer compra** | `bought: false` + lista “Comprados recentes” |
| Concluir tarefa | `PATCH .../tasks/{id}/` |
| **Compromisso feito** | `PATCH .../events/{id}/` `dismissed: true` (remove da agenda) |

## 4.2 Captura rápida ✅ implementado

- `POST /api/pwa/shopping/` — nome + qty opcional  
- `POST /api/pwa/tasks/` — título + contexto opcional  
- FAB “+” no PWA; duplicata no mercado → 409  

## 4.3 Desfazer tarefa e histórico ✅ implementado

- `PATCH .../tasks/{id}/` body `{"status": "pending"}` (reabrir) ou `"done"`  
- Snapshot: `tasks_done_recent` (7 dias) + **Reabrir** na aba Hoje  

## 4.4 Compromissos avançados ✅ implementado

- Snooze: `POST .../events/{id}/snooze/`  
- UI: **+15 min** / **Amanhã 9h**  

## 4.5 Offline e sync ⏸️ adiado

- IndexedDB + fila + Workbox Background Sync  

## 4.6 Proatividade no dispositivo ✅ implementado

- Web Push (VAPID): `GET /api/pwa/push/vapid/`, `POST .../subscribe/` / `unsubscribe/`  
- Celery `check_scheduled_reminders` e `check_upcoming_events` espelham texto no push  
- UI: botão **Notificações** no PWA; `sw-push.js` no service worker  
- Setup: `python manage.py generate_vapid_keys` → `VAPID_*` no `.env`  
- Geofence via push: 🔜 (opcional)  

## 4.7 Segurança e onboarding ✅ implementado

- Rate limit escritas PWA (Redis)  
- **Dual token:** `PWA_API_TOKEN` + `PWA_API_TOKEN_PREVIOUS` (rotação sem downtime)  
- **Pairing:** `POST /api/pwa/pairing/create/` (autenticado) → QR / URL `?code=`  
- `POST /api/pwa/pairing/exchange/` (público, one-shot) → token de sessão  
- CLI: `python manage.py generate_pwa_pairing`  

## 4.8 UX polish ✅ implementado

- Pull-to-refresh, skeleton, toast, tema claro, vibrate  

## 4.9 Observabilidade ✅ implementado

- `PwaMutationLog` + admin  
- Dashboard PWA vs Telegram — 🔜  

## 4.10 work-agent ✅ documentado

- `docs/WORK_AGENT.md` + `work-agent/CONTEXT.md` — sem código compartilhado no DB  

---

**Restante opcional:** 4.5 offline · dashboard 4.9 · push geofence.