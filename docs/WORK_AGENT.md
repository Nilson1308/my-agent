# work-agent — relação com my-agent

O **my-agent** é o assistente **pessoal/casa** (mercado, Theo, geofence, Telegram). O **work-agent** é o produto **profissional** (reuniões, action items, atas) — repositório irmão, **base de dados e secrets separados**.

## Onde está a especificação

Documento canônico (visão, entidades, MVP, arquitetura):

- [`/var/www/my-projects/work-agent/CONTEXT.md`](../../work-agent/CONTEXT.md)

## O que reutilizamos do my-agent

| Peça | my-agent (hoje) | work-agent (futuro) |
|------|-----------------|---------------------|
| Front | Vue 3 + Vite + Tailwind + vite-plugin-pwa em `/app/` | Mesma stack; rotas e auth **JWT** |
| API | Django Ninja + `X-PWA-Token` | `/api/v1/*` com sessão/JWT |
| IA | `AgentPlan` + Groq + pgvector | `WorkPlan`, entidades `Meeting` / `ActionItem` |
| Proatividade | Celery + Telegram + **Web Push PWA** | Briefing trabalho + push opcional |
| Deploy | Docker + Apache + Gunicorn | Porta/host dedicados (ex. `:8046`) |

## O que **não** misturar

- PostgreSQL / Redis / `.env` do my-agent **não** servem o work-agent.
- Tokens PWA do my-agent **não** autenticam no work-agent.
- Bot Telegram pode ser outro bot ou outra allowlist.

## PWA atual (my-agent) como referência

- Auth: `PWA_API_TOKEN` + pairing QR (`docs/PWA_BRIDGE.md`)
- Push: VAPID + `PwaPushSubscription` (lembretes Celery)
- Roadmap pessoal: `docs/ROADMAP_PWA_ONDA4.md`

## Próximo passo quando iniciar o work-agent

1. Fork do esqueleto `apps/core`, `apps/ai`, `config/` — sem models de mercado/Theo.
2. Models `Meeting`, `ActionItem`, `WorkNote` + migrações próprias.
3. PWA com login (não token estático) e proxy Apache em subdomínio ou path dedicado.
4. Alinhar `CONTEXT.md` com TI (DNS, backup, LGPD).

*Este arquivo é só documentação — nenhum código do work-agent roda dentro do my-agent.*