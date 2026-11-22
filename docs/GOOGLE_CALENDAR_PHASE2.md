# Fase 2 — Google Calendar (rascunho)

Não implementado no MVP. Diretriz para evolução futura:

## Escopo

- Sincronização **unidirecional** leitura (compromissos externos → `Event`) ou bidirecional opcional.
- OAuth 2.0 por usuário único; tokens em variáveis criptografadas ou tabela `CalendarCredential`.
- Filas Celery dedicadas (`calendar_sync`) para não bloquear o worker principal.

## Variáveis (futuro)

- `GOOGLE_CALENDAR_CLIENT_ID`
- `GOOGLE_CALENDAR_CLIENT_SECRET`
- `GOOGLE_CALENDAR_REFRESH_TOKEN`

## Tarefas técnicas

1. App Django `apps.calendar` com cliente Google API.
2. Beat: `sync_calendar_events` a cada 15–30 min.
3. Mapear `Event.external_id` para idempotência.
4. Testes com credenciais mock.

Enquanto isso, use `add_event` via Telegram.