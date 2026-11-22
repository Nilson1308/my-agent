# CONTEXT.md — Agente Pessoal Diário (MVP)

## 1. Visão Geral
Assistente pessoal via **Telegram Bot** para captura rápida (áudio ou texto em linguagem natural), organização de responsabilidades diárias, memória semântica e proatividade (briefings e lembretes).

Uso exclusivo para 1 usuário (single-tenant), focado em baixa fricção, resposta rápida e custo zero de inferência via **Groq Free**.

## 2. Stack Técnica
- **Linguagem / Backend:** Python 3.12+, Django 5.x, Django Ninja (ou DRF para webhooks/endpoints internos)
- **Banco de Dados:** PostgreSQL com extensão `pgvector` (busca semântica em ideias/notas)
- **Assincronismo & Proatividade:** Celery + Celery Beat + Redis
- **Interface Principal:** Telegram Bot API (Webhook ou Long Polling em dev)
- **IA / Inferência (Groq API - Free Tier):**
  - Transcrição de áudio: `whisper-large-v3-turbo`
  - Roteamento, extração de entidades e resposta: `llama-3.3-70b-versatile` (com Structured Outputs / JSON Mode)
  - Embeddings (local ou leve): `sentence-transformers` (ex: `intfloat/multilingual-e5-small` ou similar) ou API de embeddings compatível com `pgvector`
- **Infraestrutura:** Ubuntu Linux, Gunicorn, Nginx, Docker / Docker Compose (opcional para dev)
- **Timezone:** `America/Sao_Paulo`

## 3. Contextos e Domínios do Agente
Toda mensagem (texto ou áudio transcrito) pode conter **uma ou múltiplas intenções** simultâneas. O agente deve quebrar e classificar em:

1. **Mercado / Casa (`shopping`):**
   - Itens acabando em casa (ex: "acabou azeite e shoyu").
   - Comandos de consulta/baixa (ex: "tô indo no mercado", "já comprei o azeite").
2. **Tarefas & Pendências (`task`):**
   - Ações com ou sem prazo, categorizadas por contexto: `casa`, `theo`, `trabalho`, `pessoal`.
   - Ex: "preciso confirmar o horário do treino do Theo na quinta".
3. **Compromissos (`event`):**
   - Eventos com data e hora definidas (com suporte futuro a sync com Google Calendar).
   - Ex: "buscar o Theo na escola quinta às 17h30".
4. **Ideias & Memória (`note`):**
   - Pensamentos soltos, insights técnicos, referências e anotações rápidas.
   - Armazenadas com embedding no `pgvector` para resgate semântico posterior (ex: "qual era aquela ideia de arquitetura que tive semana passada?").
5. **Consulta (`query`):**
   - Perguntas sobre o que está pendente, agenda do dia, lista de mercado ou busca na memória vetorial.

## 4. Fluxo Principal (Pipeline)
1. Usuário envia texto ou áudio no Telegram.
2. Backend valida `TELEGRAM_ALLOWED_USER_ID` (segurança: ignora qualquer outro chat_id).
3. Se for áudio (`.ogg`), baixa o arquivo e transcreve via Groq (`whisper-large-v3-turbo`).
4. Envia o texto + data/hora atual (`America/Sao_Paulo`) para o LLM (`llama-3.3-70b-versatile`) com JSON Schema estrito.
5. O LLM retorna uma lista de ações estruturadas (`actions: [...]`).
6. O backend executa cada ação no PostgreSQL (cria item de mercado, tarefa, evento, nota com embedding ou executa busca).
7. O bot responde no Telegram confirmando de forma curta e escaneável o que foi registrado/encontrado.

## 5. Proatividade & Automações
- **Briefing Matinal (Celery Beat — 07h30 diário):**
  - Envia mensagem única no Telegram com: compromissos do dia, tarefas atrasadas/para hoje e pendências do contexto `theo`.
- **Lembretes de Compromissos (Celery Beat — a cada 15 min):**
  - Notifica no Telegram 30 minutos antes de qualquer evento agendado.
- **Webhook de Geofencing (`POST /api/webhooks/geofence/`):**
  - Endpoint autenticado por token simples no header (`X-Webhook-Token`).
  - Recebe gatilho do celular (MacroDroid / Atalhos) ao chegar no mercado e dispara imediatamente a lista de compras ativa no Telegram.

## 6. Modelagem Inicial (Django Models)
- `ShoppingItem`: `name`, `quantity` (opcional), `is_bought` (bool), `created_at`, `bought_at`
- `Task`: `title`, `context` (choices: casa, theo, trabalho, pessoal), `due_date` (nullable), `status` (pending, done), `created_at`
- `Event`: `title`, `context`, `start_at`, `end_at` (nullable), `reminded` (bool), `created_at`
- `Note`: `content`, `context`, `embedding` (`VectorField`), `created_at`
- `InteractionLog`: `raw_input`, `input_type` (text/audio), `parsed_json`, `bot_response`, `created_at`

## 7. Variáveis de Ambiente (.env)
- `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`
- `DATABASE_URL` (PostgreSQL com pgvector)
- `REDIS_URL`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_USER_ID`
- `GROQ_API_KEY`
- `GEOFENCE_WEBHOOK_TOKEN`

## 8. Diretrizes de Código para o Agente (Cursor)
- Manter arquitetura limpa e modular: separar `apps/core`, `apps/bot`, `apps/ai` e `apps/memory`.
- Lógica de negócio em `services.py`, nunca inflar views ou handlers do Telegram.
- Usar tipagem Python (`type hints`) e Pydantic para validar os Structured Outputs da Groq.
- Tratar falhas de rede/API da Groq e Telegram com fallback amigável ao usuário.
- Priorizar entrega incremental (MVP funcional primeiro, otimizações depois).

## 9. Roadmap de Execução (Fase 1 - MVP)
1. Setup do projeto Django + PostgreSQL (`pgvector`) + Redis + Celery.
2. Criação dos models e migrations.
3. Serviço `apps/ai/groq_service.py` (Whisper + Llama 3.3 JSON router).
4. Bot Telegram (webhook/polling) com trava de `TELEGRAM_ALLOWED_USER_ID`.
5. Task Celery Beat para Briefing Matinal e lembretes.
6. Endpoint de webhook para Geofencing do mercado.