from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404

PWA_DIST = Path(settings.BASE_DIR) / "pwa" / "dist"


def serve_pwa(request, path: str = ""):
    """
    SPA estática em /app/ quando o proxy manda tudo ao Gunicorn.
    Em produção ideal o Apache serve `pwa/dist` (Alias); isto é fallback seguro.
    """
    if not PWA_DIST.is_dir():
        raise Http404("PWA build ausente (rode ./deploy/build-pwa.sh).")

    rel = (path or "").lstrip("/")
    if not rel or "/" not in rel and "." not in Path(rel).name:
        candidate = PWA_DIST / "index.html"
    else:
        candidate = (PWA_DIST / rel).resolve()
        root = PWA_DIST.resolve()
        if not str(candidate).startswith(str(root)):
            raise Http404()
        if not candidate.is_file():
            candidate = PWA_DIST / "index.html"

    if not candidate.is_file():
        raise Http404()

    content_type = None
    suffix = candidate.suffix.lower()
    if suffix == ".js":
        content_type = "application/javascript"
    elif suffix == ".css":
        content_type = "text/css"
    elif suffix == ".svg":
        content_type = "image/svg+xml"
    elif suffix == ".webmanifest":
        content_type = "application/manifest+json"

    return FileResponse(candidate.open("rb"), content_type=content_type)