# Onda 5 — Chat, áudio, documentos, mapa (PWA + Telegram)

Mesmo **cérebro** (`run_agent_message`) nos dois canais; Telegram **não** é desativado.

## 5.1 Chat texto PWA + Telegram ✅

- `POST /api/pwa/chat/` — `{"text": "..."}` → `reply`, `llm_outcome`, `interaction_log_id`
- `InteractionLog.channel` = `telegram` | `pwa`
- Bot refatorado para `apps.memory.agent_pipeline.run_agent_message`

## 5.2 Áudio curto no PWA ✅

- `POST /api/pwa/chat/audio/` — multipart `audio` → Whisper → mesma pipeline
- UI: botão 🎤 na aba Chat (gravar/parar)
- Limite: `PWA_AUDIO_MAX_BYTES` (default 5 MB)

## 5.3 Mapa MacroDroid + log geofence ✅

- Modelo `GeofenceEvent` em cada `POST /api/webhooks/geofence/`
- Body opcional: `"lat"`, `"lon"` além de `"location"`
- `GET /api/pwa/geofence/events/` — lista para o PWA
- Aba **Mapa** (Leaflet + OSM) + histórico textual
- `/macro/` atualizado com exemplo lat/lon

## 5.4 PDF → notas (RAG local) 🔜

- Extrair texto, chunks, embedding fastembed

## 5.5 Foto + vision (limite diário) 🔜

---

**Ordem restante:** 5.4 → 5.5