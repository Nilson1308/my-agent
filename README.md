# Agente Pessoal Diário (MVP)

Scaffolding Django — Fase 1 (setup + models). Veja `context.md` para visão completa do produto.

## Pré-requisitos

- Python 3.12+
- Docker e Docker Compose

## Configuração rápida

```powershell
# 1. Ambiente Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Variáveis de ambiente
Copy-Item .env.example .env
# Edite .env (SECRET_KEY, tokens, etc.)

# 3. Infraestrutura local
docker compose up -d

# 4. Banco de dados
python manage.py migrate

# 5. Superusuário (opcional, para o /admin)
python manage.py createsuperuser
```

## Executar em desenvolvimento

Terminal 1 — Django:

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

Terminal 2 — Celery worker:

```powershell
.\.venv\Scripts\Activate.ps1
celery -A config worker -l info
```

Terminal 3 — Celery Beat (agendamentos):

```powershell
.\.venv\Scripts\Activate.ps1
celery -A config beat -l info
```

Terminal 4 — Bot Telegram (long polling, dev):

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py run_bot
```

Requer `TELEGRAM_BOT_TOKEN` e `TELEGRAM_ALLOWED_USER_ID` no `.env`.

**Briefing matinal manual (teste proativo):**

```powershell
python manage.py test_briefing
```

**Webhook de geofencing (lista de mercado no Telegram):**

Com `runserver` ativo e `GEOFENCE_WEBHOOK_TOKEN` no `.env`:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/webhooks/geofence/" `
  -H "Content-Type: application/json" `
  -H "X-Webhook-Token: SEU_GEOFENCE_WEBHOOK_TOKEN" `
  -d "{\"location\": \"mercado\"}"
```

Admin: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

**Testes:**

```bash
python manage.py test apps.core apps.memory
# produção (Docker):
docker-compose -f docker-compose.prod.yml exec web python manage.py test apps.core apps.memory
```

**Health (produção):** `GET https://copa.mogidascruzes.sp.gov.br/api/health/`

## Estrutura

- `config/` — settings, URLs, WSGI/ASGI, Celery
- `apps/core/` — API Ninja (webhook geofencing)
- `apps/bot/` — bot Telegram (handlers + `run_bot`)
- `apps/ai/` — Groq / roteamento LLM (futuro)
- `apps/memory/` — models, Celery tasks, memória semântica (`pgvector`)

## Deploy em Produção (VPS Ubuntu)

**Apache2 (recomendado neste projeto em produção):** veja `deploy/PRODUCTION_APACHE.md` e `AGENTS.md` (instruções para agentes Cursor). Exemplo de vhost: `deploy/apache2.my-agent.conf.example`.

Pré-requisitos na VPS: Docker, Docker Compose plugin e proxy reverso (Apache2 ou Nginx).

```bash
# 1. Clonar o repositório
git clone <URL_DO_REPO> my-agent
cd my-agent

# 2. Configurar ambiente
cp .env.example .env
nano .env
```

Ajustes importantes no `.env` de produção:

```env
DEBUG=False
ALLOWED_HOSTS=seudominio.com,127.0.0.1
DATABASE_URL=postgresql://my_agent:SENHA_FORTE@db:5432/my_agent
REDIS_URL=redis://redis:6379/0
POSTGRES_DB=my_agent
POSTGRES_USER=my_agent
POSTGRES_PASSWORD=SENHA_FORTE
```

```bash
# 3. Subir stack
docker compose -f docker-compose.prod.yml up -d --build

# 4. Migrations e admin
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# 5. (Opcional) backfill de embeddings de notas antigas
docker compose -f docker-compose.prod.yml exec web python manage.py reindex_notes
```

**Nginx (proxy reverso + TLS):**

```bash
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/my-agent
# edite server_name
sudo ln -s /etc/nginx/sites-available/my-agent /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d seudominio.com
```

O Gunicorn fica exposto apenas em `127.0.0.1:8000` no host; o Nginx faz proxy para a API (`/api/webhooks/geofence/`) e o `/admin/`.

Serviços em produção (`docker-compose.prod.yml`): `db`, `redis`, `web`, `bot`, `celery_worker`, `celery_beat` (todos com `restart: unless-stopped`). O volume `fastembed_cache` evita rebaixar o modelo ONNX a cada restart.