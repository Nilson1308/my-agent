# Instruções para agentes Cursor — deploy Apache2 (SSH / produção)

Use este arquivo quando o usuário pedir **publicar, atualizar ou depurar produção** do repositório `my-agent`.

## Contexto do projeto

- **Stack:** Django 5, Gunicorn (container `web`), PostgreSQL+pgvector, Redis, Celery, bot Telegram (`run_bot`), Groq, embeddings fastembed, TTS edge-tts.
- **Repo:** `https://github.com/Nilson1308/my-agent.git`, branch principal `main`.
- **Compose produção:** `docker-compose.prod.yml` (serviços: `db`, `redis`, `web`, `bot`, `celery_worker`, `celery_beat`).
- **Doc detalhada:** `deploy/PRODUCTION_APACHE.md`
- **Vhost exemplo:** `deploy/apache2.my-agent.conf.example` (substituir `deploy/nginx.conf.example` quando o host for **Apache2**, não Nginx).

## Papel do agente

1. **Preparar no repositório local** (commits, README, configs) se o usuário pedir.
2. **Gerar comandos SSH/bash** claros para o servidor; o usuário costuma fazer **`git pull` no servidor** manualmente.
3. **Não** inventar segredos; **não** pedir para commitar `.env`.
4. **Não** executar SSH no servidor a menos que o usuário tenha configurado terminal/SSH no Cursor e pedido explicitamente.
5. Mudanças de código: manter diff mínimo; seguir estilo existente em `apps/` e `config/`.

## Premissas de produção

| Item | Valor típico |
|------|----------------|
| Caminho do clone | `/var/www/my-agent` (confirmar com o usuário) |
| App HTTP interno | `http://127.0.0.1:8045` (host; container escuta 8000) |
| Proxy público | Apache2 → `ProxyPass / http://127.0.0.1:8045/` |
| Domínio (este servidor) | `copa.mogidascruzes.sp.gov.br` → `deploy/apache/copa.mogidascruzes.sp.gov.br.conf` |
| Migrations | Sempre após deploy: `docker compose -f docker-compose.prod.yml exec web python manage.py migrate --noinput` |
| Rebuild | `docker compose -f docker-compose.prod.yml up -d --build` se `requirements.txt`, `Dockerfile` ou código Python mudou |

## Fluxo padrão após `git pull` (copiar para o usuário)

```bash
cd /var/www/my-projects/my-agent   # ou /var/www/my-agent no seu clone
git pull origin main
./deploy/reload-prod.sh
```

Só mudou `.env` (tokens, ALLOWED_HOSTS, etc.):

```bash
./deploy/reload-prod.sh --env-only
```

## Script `deploy/reload-prod.sh`

| Flag | Efeito |
|------|--------|
| (nenhuma) | `up -d --build`, migrate, collectstatic, smoke `/admin/login/` |
| `--env-only` | `up -d --force-recreate` em `web`, `bot`, `celery_worker`, `celery_beat` |
| `--no-build` | `up -d` sem rebuild |
| `--no-migrate` | Pula migrate/collectstatic |

## Apache2 — checklist do agente

Ao criar ou revisar vhost:

- Módulos: `proxy`, `proxy_http`, `headers`, `ssl`, `rewrite`
- `ProxyPreserveHost On`
- `RequestHeader set X-Forwarded-Proto` → `http` ou `https` conforme o vhost
- `LimitRequestBody` ≥ 20MB se houver uploads grandes
- Lembrar `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` no `.env` do **servidor**
- TLS: `certbot --apache -d <domínio>`

Não documentar Nginx para este servidor se o usuário disse **Apache2**.

## Variáveis críticas (`.env` no servidor)

`SECRET_KEY`, `DEBUG=False`, `DATABASE_URL`, `REDIS_URL`, `POSTGRES_*`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_ID`, `GROQ_API_KEY`, `GEOFENCE_WEBHOOK_TOKEN`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`.

Opcional: `TELEGRAM_BOOTSTRAP_RETRIES=-1`, `TTS_*`, proxy Telegram se a rede bloquear API.

## Verificação pós-deploy (roteiro)

1. `curl` em `127.0.0.1:8000/admin/login/` no servidor → 200/302  
2. `curl` HTTPS no domínio → 200/302  
3. Logs `bot` sem `NetworkError` contínuo  
4. Mensagem de teste no Telegram  
5. Webhook geofence com token (se usado)

## O que evitar

- Commitar `.env`, tokens ou `SECRET_KEY`.
- `git push --force` em `main` sem pedido explícito.
- Remover volumes Docker (`pgdata`) sem backup.
- Expor porta 8000 publicamente no firewall (só Apache).
- Instalar Python/venv no host para servir o app; produção é **Docker + proxy Apache**.

## Referências no repo

- `README.md` — desenvolvimento local  
- `context.md` — visão do produto  
- `deploy/PRODUCTION_APACHE.md` — runbook completo  
- `deploy/apache2.my-agent.conf.example` — VirtualHost  

Quando o usuário pedir “instruções para novo agente”, aponte para **este `AGENTS.md`** e **`deploy/PRODUCTION_APACHE.md`**.