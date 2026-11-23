# Stack PWA — My Agent

Decisões fixas (Nov/2025):

| Tópico | Escolha |
|--------|---------|
| Hosting | `https://copa…/app/` |
| Stack | Vue 3 + Vite 6 + Tailwind 4 + vite-plugin-pwa |
| Auth | `PWA_API_TOKEN` em `sessionStorage` → header `X-PWA-Token` |
| Escopo v0 | Somente leitura (`GET /api/pwa/snapshot/`) |
| Nome na UI | **My Agent** |
| API write | Fase seguinte (PATCH mercado, etc.) |

## Repositório

`my-agent/pwa/` — build com `npm run build` → `pwa/dist/`.

Apache: `Alias /app` + `ProxyPass /app !` — ver `deploy/apache/copa.mogidascruzes.sp.gov.br.conf`.

## Produção

1. `PWA_API_TOKEN` no `.env` do Docker.
2. `./deploy/build-pwa.sh`
3. `sudo cp deploy/apache/copa…conf` e `apache2ctl configtest && systemctl reload apache2`

## Dev

```bash
cd pwa && npm install && npm run dev
# http://localhost:5174/app/
```

`VITE_DEV_API=http://127.0.0.1:8045` se a API não estiver no mesmo host do Vite.

## Relação work-agent

Mesma stack front; outro backend, JWT e rota `/api/v1/*` — ver `work-agent/CONTEXT.md`.