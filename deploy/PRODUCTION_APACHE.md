# Produção — VPS com Apache2, Docker e `git pull`

Repositório: `https://github.com/Nilson1308/my-agent.git`

O **Gunicorn** roda dentro do Docker (`web`) em `127.0.0.1:8000`. O **Apache2** no host faz proxy reverso para essa porta. O **bot Telegram**, **Celery worker** e **Celery beat** são containers separados (`docker-compose.prod.yml`).

## Arquitetura

```text
Internet → Apache2 (:443) → 127.0.0.1:8000 (container web/Gunicorn)
MacroDroid → POST /api/webhooks/geofence/
Telegram ← long polling (container bot, saída HTTPS)
PostgreSQL (pgvector) + Redis — containers db/redis
```

## Pré-requisitos no servidor (Ubuntu/Debian)

- Git, Docker Engine, plugin Docker Compose v2
- Apache2
- Usuário SSH com sudo (ou root, se for o fluxo do time)
- Porta 80/443 liberada; **8000 só em localhost** (já definido no compose)

```bash
sudo apt update
sudo apt install -y git apache2
# Docker: siga a documentação oficial da distro
sudo a2enmod proxy proxy_http headers ssl rewrite
sudo systemctl enable --now apache2
```

## Primeiro deploy (uma vez)

### 1. Clonar e diretório sugerido

```bash
sudo mkdir -p /var/www
sudo chown "$USER:$USER" /var/www
cd /var/www
git clone https://github.com/Nilson1308/my-agent.git my-agent
cd my-agent
```

### 2. `.env` de produção (nunca versionar)

```bash
cp .env.example .env
nano .env
```

| Variável | Produção |
|----------|----------|
| `DEBUG` | `False` |
| `SECRET_KEY` | chave longa e aleatória |
| `ALLOWED_HOSTS` | domínio público e/ou IP da VPS |
| `CSRF_TRUSTED_ORIGINS` | `https://seudominio.com` |
| `DATABASE_URL` | `postgresql://USER:SENHA@db:5432/my_agent` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `POSTGRES_*` | iguais ao compose |
| Tokens Telegram, Groq, `GEOFENCE_WEBHOOK_TOKEN` | valores reais |

Confirme: **`.env` não vai para o Git** (está no `.gitignore`).

### 3. Stack Docker

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py migrate --noinput
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
# Opcional: embeddings de notas existentes
docker compose -f docker-compose.prod.yml exec web python manage.py reindex_notes
```

Verificar:

```bash
docker compose -f docker-compose.prod.yml ps
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/admin/login/
```

Esperado: `200` ou `302`.

### 4. Apache2

```bash
sudo cp deploy/apache2.my-agent.conf.example /etc/apache2/sites-available/my-agent.conf
sudo nano /etc/apache2/sites-available/my-agent.conf   # ServerName
sudo a2dissite 000-default.conf   # opcional, se só este site
sudo a2ensite my-agent.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

TLS (Let's Encrypt):

```bash
sudo apt install -y certbot python3-certbot-apache
sudo certbot --apache -d seudominio.com
```

No `.env`, `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` devem incluir o domínio HTTPS.

### 5. Webhook geofencing (MacroDroid)

URL pública:

```text
POST https://seudominio.com/api/webhooks/geofence/
Header: X-Webhook-Token: <GEOFENCE_WEBHOOK_TOKEN>
Body JSON: {"location": "mercado"}
```

---

## Atualização de produção (`git pull`)

Fluxo que o operador humano executa no servidor (o agente no Cursor **só propõe** estes comandos; não assume acesso SSH):

```bash
cd /var/www/my-agent    # ajuste se o clone estiver em outro path
git fetch origin
git pull origin main

docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py migrate --noinput
```

Reinício leve (sem rebuild), se só mudou Python sem deps:

```bash
docker compose -f docker-compose.prod.yml restart web bot celery_worker celery_beat
```

Após mudança em `requirements.txt` ou `Dockerfile`, use sempre `--build`.

### Smoke test pós-deploy

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=50 web bot
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/admin/login/
# no seu PC:
curl -sS -o /dev/null -w "%{http_code}\n" https://seudominio.com/admin/login/
```

Teste Telegram: mensagem de texto ao bot; voz se `TTS_ENABLED=True`.

---

## Logs e troubleshooting

```bash
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f bot
sudo tail -f /var/log/apache2/error.log
sudo tail -f /var/log/apache2/access.log
```

| Sintoma | Causa provável |
|---------|----------------|
| 502 Bad Gateway | container `web` parado; `docker compose ps` |
| 400 Invalid HTTP_HOST | `ALLOWED_HOSTS` no `.env` |
| CSRF no admin | `CSRF_TRUSTED_ORIGINS` |
| Bot offline | logs do serviço `bot`; token Telegram |
| Webhook 401 | `GEOFENCE_WEBHOOK_TOKEN` / header |

---

## Rollback

```bash
cd /var/www/my-agent
git log -5 --oneline
git checkout <commit-anterior>
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py migrate --noinput
```

Prefira branch estável e releases tagueadas se o deploy for frequente.

---

## O que **não** colocar no Apache

Não sirva o projeto com `mod_wsgi` + venv no host **em paralelo** ao Docker: use apenas **proxy** para `127.0.0.1:8000` como neste guia.