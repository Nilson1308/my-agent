# CONTEXT.md — Agente Pessoal Diário (MVP)

## 1. Visão Geral
Assistente pessoal via **Telegram Bot** para captura rápida (áudio ou texto em linguagem natural), organização de responsabilidades diárias, memória semântica e proatividade (briefings e lembretes).

Uso exclusivo para 1 usuário (single-tenant), focado em baixa fricção, resposta rápida e custo baixo de inferência via **Groq**.

## 2. Stack Técnica
- **Linguagem / Backend:** Python 3.12+, Django 5.x, Django Ninja (`/api/`)
- **Banco de Dados:** PostgreSQL com extensão `pgvector` (busca semântica em ideias/notas)
- **Assincronismo & Proatividade:** Celery + Celery Beat + Redis (`redis-py` ≥ 6.1)
- **Interface Principal:** Telegram Bot API (long polling em produção no container `bot`)
- **IA / Inferência (Groq API):**
  - Transcrição de áudio: `whisper-large-v3-turbo` (`GROQ_WHISPER_MODEL`)
  - Roteamento e extração: modelo configurável em `GROQ_LLM_MODEL` (padrão atual no `.env`: `openai/gpt-oss-120b`) com JSON estruturado (Pydantic `AgentPlan`)
  - Embeddings locais: **fastembed** (`paraphrase-multilingual-MiniLM-L12-v2`, 384 dims)
- **Infraestrutura (produção neste servidor):** Docker Compose (`docker-compose.prod.yml`), Gunicorn no container `web` em `127.0.0.1:8045`, **Apache2** proxy para `https://copa.mogidascruzes.sp.gov.br`
- **Timezone:** `America/Sao_Paulo`
- **Deploy:** `./deploy/reload-prod.sh` (build/migrate/collectstatic); `collectstatic` no entrypoint do Gunicorn

## 3. Contextos e Domínios do Agente
Toda mensagem (texto ou áudio transcrito) pode conter **uma ou múltiplas intenções** simultâneas. O agente deve quebrar e classificar em:

1. **Mercado / Casa (`shopping`):**
   - Itens acabando em casa (ex: "acabou azeite e shoyu").
   - Comandos de consulta/baixa (ex: "tô indo no mercado", "já comprei o azeite").
2. **Tarefas & Pendências (`task`):**
   - Ações com ou sem prazo, categorizadas por contexto: `casa`, `theo`, `trabalho`, `pessoal`.
3. **Compromissos (`event`):**
   - Eventos com data e hora definidas (sync Google Calendar — futuro).
4. **Ideias & Memória (`note`):**
   - Notas com embedding `pgvector` para busca semântica.
5. **Consulta (`query`):**
   - Perguntas sobre pendências, agenda, mercado ou memória.

## 4. Fluxo Principal (Pipeline)
1. Usuário envia texto ou áudio no Telegram.
2. Backend valida `TELEGRAM_ALLOWED_USER_ID` (ignora outros `chat_id`).
3. Áudio: transcrição Groq (`whisper-large-v3-turbo`).
4. Texto + contexto temporal (`America/Sao_Paulo`) → LLM (`GROQ_LLM_MODEL`) → `AgentPlan`.
5. `apps/memory/services.execute_agent_plan` persiste no PostgreSQL.
6. Resposta curta no Telegram; envio síncrono compartilhado em `apps/bot/telegram_client.py`.

## 5. Proatividade & Automações
- **Briefing Matinal (Celery Beat — 07h30):** compromissos do dia, tarefas atrasadas/para hoje, pendências `theo`, **lista de mercado ativa** (ou “lista vazia”).
- **Lembretes de Compromissos (a cada 15 min):** ~30 min antes do `start_at` (janela 35 min no código).
- **Webhook Geofencing** `POST /api/webhooks/geofence/`:
  - Header `X-Webhook-Token` (`GEOFENCE_WEBHOOK_TOKEN`; comparação com `secrets.compare_digest`).
  - Rate limit por IP via Redis (`GEOFENCE_RATE_LIMIT_SECONDS`, padrão 120).
  - Resposta JSON: `status`, `items_count`, `telegram_sent` (`sent` | `empty` | `telegram_failed`).
  - Lista vazia: envia mensagem curta no Telegram + `status=empty`.
  - MacroDroid / Atalhos no celular (domínio público **copa**).

## 6. Modelagem Inicial (Django Models)
- `ShoppingItem`, `Task`, `Event`, `Note` (+ `VectorField`), `InteractionLog` — ver `apps/memory/models.py`.

## 7. Variáveis de Ambiente (.env)
- `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`, `REDIS_URL`, `POSTGRES_*`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_ID`
- `GROQ_API_KEY`, `GROQ_LLM_MODEL`, `GROQ_WHISPER_MODEL`
- `GEOFENCE_WEBHOOK_TOKEN`, `GEOFENCE_RATE_LIMIT_SECONDS`
- TTS: `TTS_ENABLED`, `TTS_VOICE`, `TTS_MAX_CHARS`

## 8. API interna
- `GET /api/health/` — PostgreSQL + Redis (sem autenticação; inclui contador `telegram_send_failures` se Redis disponível).

## 9. Diretrizes de Código
- Lógica em `services.py`; Telegram síncrono centralizado em `telegram_client.py`.
- Tipagem + Pydantic para saídas Groq.
- Testes: `python manage.py test apps.core apps.memory`.

## 10. Infra e evolução
- **Compose:** `name: my-agent` (`docker-compose -p my-agent -f docker-compose.prod.yml`).
- **Backup DB:** `./deploy/backup-pgdata.sh` (retenção 14 dias em `backups/`).
- **MacroDroid:** página `/macro/` (instruções curl; token não exposto).
- **Google Calendar:** fase 2 — `docs/GOOGLE_CALENDAR_PHASE2.md`.

## 11. Modelagem / LLM
- Mercado: constraint única em `ShoppingItem.name` enquanto `is_bought=False`; `add_shopping` idempotente (iexact).
- Lembretes: `EVENT_REMINDER_MINUTES_BEFORE` (30) ± `EVENT_REMINDER_WINDOW_MINUTES` (8).
- `InteractionLog.llm_outcome` + comando `python manage.py review_llm_logs`.
- `parse_user_message` → `LlmParseResult` (ok, fallback, parse_error, groq_rate_limit, …).

## 12. Roadmap (pós-MVP)
- CI pytest, hardening admin, body form no geofence (MacroDroid).