from __future__ import annotations

import secrets

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Gera um token seguro para PWA_API_TOKEN (cole no .env e na tela /app/)."

    def handle(self, *args, **options) -> None:
        token = secrets.token_urlsafe(32)
        self.stdout.write(self.style.SUCCESS(token))
        self.stdout.write("")
        self.stdout.write("Adicione ao .env:")
        self.stdout.write(f"PWA_API_TOKEN={token}")
        self.stdout.write("Recrie o container web: ./deploy/reload-prod.sh --env-only")