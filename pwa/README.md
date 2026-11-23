# My Agent PWA

UI instalável em **`https://<host>/app/`** (leitura + marcar mercado/tarefa).

## Desenvolvimento

```bash
cd pwa
npm install
# API local (Gunicorn em :8045 ou dev Django em :8000)
VITE_DEV_API=http://127.0.0.1:8045 npm run dev
```

Abra `http://localhost:5174/app/` e cole o `PWA_API_TOKEN`.

## Build produção

```bash
npm ci && npm run build
```

Saída em `pwa/dist/`. O Apache serve esse diretório em `/app/` (ver `deploy/apache/`).

## Token

- Token manual: `PWA_API_TOKEN` no `.env` (também aceita `PWA_API_TOKEN_PREVIOUS` na rotação).
- Pairing: link `?code=…` ou QR (**QR aparelho** no app / `python manage.py generate_pwa_pairing`).
- Armazenado em `sessionStorage` (sessão do navegador).

**Web Push:** defina `VAPID_*` no servidor (`python manage.py generate_vapid_keys`) e toque **Notificações** no app.

## Instalar no celular

1. Abra `/app/` no Chrome ou Safari.
2. Faça login com o token.
3. **Android (Chrome):** menu ⋮ → “Instalar app” ou “Adicionar à tela inicial”.
4. **iPhone (Safari):** Compartilhar → “Adicionar à Tela de Início”.