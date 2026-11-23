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

## 4.4 Compromissos avançados

- Snooze: `POST .../events/{id}/snooze/` (+15 min / amanhã)  
- Ou campo `Event.dismissed_at` em vez de delete (auditoria)  

## 4.5 Offline e sync

- IndexedDB: último snapshot + fila de PATCH  
- Background Sync (Workbox) quando voltar online  
- Badge “offline · pendências na fila”  

## 4.6 Proatividade no dispositivo

- Web Push (VAPID) para lembrete/compromisso — espelhar Celery  
- Opcional: notificação “geofence” via PWA se permissão  

## 4.7 Segurança e onboarding

- Rate limit por IP no namespace `/api/pwa/*`  
- Página “pairing”: QR com token de uso único gerado no admin  
- Rotação `PWA_API_TOKEN` sem downtime (dois tokens válidos)  

## 4.8 UX polish

- Pull-to-refresh, loading skeletons, toast de sucesso  
- `navigator.vibrate` no ✓ (Android)  
- Tema claro / `prefers-color-scheme`  

## 4.9 Observabilidade

- `PwaMutationLog` (item, ação, ip, timestamp) — debug e métricas  
- Dashboard admin: uso PWA vs Telegram  

## 4.10 work-agent

- Reusar stack; JWT; entidades Meeting/ActionItem — não misturar DB com my-agent  

---

**Ordem sugerida:** 4.1 → 4.2 → 4.3 → 4.5 → 4.6 → 4.8 → 4.4/4.6 push.