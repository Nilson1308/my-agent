# Roadmap de interação e confiabilidade — my-agent

**Status:** Ondas 1–3 concluídas no bot/API (Nov/2025). Próximo: **work-agent** (PWA profissional).

---

## Onda 1 — Curto prazo ✅

| # | Entrega |
|---|---------|
| 1.1 | Botões Sim / Não / Ver lista (duplicatas) |
| 1.2 | Respostas curtas + `reply_hint` no topo |
| 1.3 | `/help` e `/comandos` |
| 1.4 | Áudio: linha “Registrei: …” no TTS |
| 1.5 | Echo leve (`reply_hint`) sem mini-wizard |

---

## Onda 2 — Médio prazo ✅

| # | Entrega |
|---|---------|
| 2.1 | `/hoje` + filtros |
| 2.2 | `Task.due_at` + lembrete opcional |
| 2.3 | Duplicata em notas (vetorial) |
| 2.4 | `/desfazer` (5 min) |
| 2.5 | Feedback 👍/👎 |
| 2.6 | Confirmação em `clear_*` / deletes múltiplos |

---

## Onda 3 — Longo prazo ✅ (escopo my-agent)

| # | Entrega | Notas |
|---|---------|--------|
| 3.1 | PWA complementar ✅ v0 | `my-agent/pwa` em `/app/` (leitura); ver `docs/PWA_STACK.md` |
| 3.2 | Preferências | `UserPreferences` + `/prefs` |
| 3.3 | Atalhos sem Groq | `/lista`, `/resumo` |
| 3.4 | Google Calendar | **Não implementado** — ver `docs/GOOGLE_CALENDAR_PHASE2.md` |

---

## Faixa técnica

| Item | Status |
|------|--------|
| `llm_outcome` + `review_llm_logs` | Feito |
| Testes golden (comandos diretos) | `test_onda3` |
| Event = compromisso com `start_at`; Reminder = disparo Celery | `context.md` |
| Backup cron | Feito |

---

## Evolução sugerida (pós-roadmap)

1. **work-agent** — PWA primário, reuniões e action items.  
2. Google Calendar quando houver credenciais OAuth.  
3. Golden prompts do Groq em CI (com mocks).