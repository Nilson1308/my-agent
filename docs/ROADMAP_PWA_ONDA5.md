# Onda 5 — Chat, áudio, documentos, mapa (PWA + Telegram)

Mesmo **cérebro** (`run_agent_message`) nos dois canais; Telegram **não** é desativado.

## 5.1 Chat texto PWA + Telegram ✅

- `POST /api/pwa/chat/` — `{"text": "..."}` → `reply`, `llm_outcome`, `interaction_log_id`
- `InteractionLog.channel` = `telegram` | `pwa`
- Bot refatorado para `apps.memory.agent_pipeline.run_agent_message`

## 5.2 Áudio curto no PWA 🔜

- Upload multipart → Whisper → mesma pipeline
- Compartilha cotas Groq com o bot

## 5.3 Mapa MacroDroid + log geofence 🔜

- `GeofenceEvent` + UI Leaflet no PWA

## 5.4 PDF → notas (RAG local) 🔜

- Extrair texto, chunks, embedding fastembed

## 5.5 Foto + vision (limite diário) 🔜

---

**Ordem:** 5.1 → 5.3 → 5.2 → 5.4 → 5.5