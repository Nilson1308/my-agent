from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.core.pwa_pairing import create_pairing_code, pairing_ttl_seconds


class Command(BaseCommand):
    help = "Gera URL/código de pairing (QR) para conectar um aparelho ao PWA sem digitar o token."

    def handle(self, *args, **options) -> None:
        if not (settings.PWA_API_TOKEN or "").strip():
            raise CommandError("Defina PWA_API_TOKEN no .env antes de gerar pairing.")
        try:
            code = create_pairing_code()
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc

        base = (settings.PWA_PUBLIC_BASE_URL or "").strip().rstrip("/") or "https://copa.mogidascruzes.sp.gov.br/app"
        if not base.endswith("/app"):
            base = f"{base}/app" if "/app" not in base else base
        pair_url = f"{base}/?code={code}"
        ttl = pairing_ttl_seconds()
        self.stdout.write(self.style.SUCCESS(pair_url))
        self.stdout.write(f"Expira em {ttl // 60} min (uso único).")
        self.stdout.write("")
        self.stdout.write("Gere QR a partir desta URL (leitor de QR do aparelho novo).")