from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse


def macro_setup_page(request: HttpRequest) -> HttpResponse:
    """Página estática com instruções MacroDroid (sem expor tokens)."""
    host = (request.get_host() or "copa.mogidascruzes.sp.gov.br").split(":")[0]
    proto = "https"
    url = f"{proto}://{host}/api/webhooks/geofence/"
    rate = int(getattr(settings, "GEOFENCE_RATE_LIMIT_SECONDS", 120))
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>MacroDroid — Geofence my-agent</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 42rem; line-height: 1.5; }}
    code, pre {{ background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 4px; }}
    pre {{ padding: 1rem; overflow-x: auto; }}
  </style>
</head>
<body>
  <h1>Lista de mercado (MacroDroid)</h1>
  <p>Configure o header <code>X-Webhook-Token</code> com o valor de
  <code>GEOFENCE_WEBHOOK_TOKEN</code> no servidor (não aparece aqui).</p>
  <h2>HTTP Request</h2>
  <ul>
    <li><strong>Método:</strong> POST</li>
    <li><strong>URL:</strong> <code>{url}</code></li>
    <li><strong>Content-Type:</strong> application/json</li>
    <li><strong>Body:</strong> <code>{{"location":"mercado"}}</code></li>
  </ul>
  <h2>Teste (no PC com token)</h2>
  <pre>curl -X POST "{url}" \\
  -H "Content-Type: application/json" \\
  -H "X-Webhook-Token: SEU_TOKEN" \\
  -d '{{"location":"mercado"}}'</pre>
  <p>Resposta esperada: <code>status</code>, <code>items_count</code>, <code>telegram_sent</code>.
  Rate limit: {rate}s por IP.</p>
  <p><a href="/api/health/">Health API</a></p>
</body>
</html>"""
    return HttpResponse(html, content_type="text/html; charset=utf-8")