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

## 5.4 PDF → notas (RAG local) ✅

- `POST /api/pwa/documents/pdf/` — `file` + `context` (form)
- pypdf → trechos (~1k chars) → `Note` + embedding fastembed (sem Groq)
- Limites: `PWA_PDF_MAX_BYTES`, `PWA_PDF_MAX_CHUNKS`
- PWA: **Enviar PDF** na aba Chat; consulta via `search_notes` no chat

## 5.5 Foto + vision (limite diário) ✅

- `POST /api/pwa/documents/image/` — vision Groq (`GROQ_VISION_MODEL`) → notas + embedding
- Limite: `PWA_VISION_MAX_PER_DAY` (Redis), `PWA_IMAGE_MAX_BYTES`
- PWA: **Foto / OCR** na aba Chat (câmera ou galeria)

---

**Onda 5 concluída** (próximas ideias: confirmação duplicata no PWA, offline 4.5).