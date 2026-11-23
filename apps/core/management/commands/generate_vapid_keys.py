from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Gera chaves VAPID para Web Push do PWA (cole no .env)."

    def handle(self, *args, **options) -> None:
        try:
            from py_vapid import Vapid
        except ImportError:
            self.stderr.write(
                "Instale py-vapid no ambiente de build ou gere manualmente.\n"
                "Após `pip install pywebpush`, tente: pip install py-vapid"
            )
            return

        from cryptography.hazmat.primitives import serialization
        from py_vapid.utils import b64urlencode

        vapid = Vapid()
        vapid.generate_keys()
        raw = vapid.public_key.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
        public_key = b64urlencode(raw)
        private_pem = vapid.private_pem()
        if isinstance(private_pem, bytes):
            private_pem = private_pem.decode("utf-8")
        private_key = private_pem.replace("\n", "\\n")

        self.stdout.write(self.style.SUCCESS(f"VAPID_PUBLIC_KEY={public_key}"))
        self.stdout.write(self.style.SUCCESS(f"VAPID_PRIVATE_KEY={private_key}"))
        self.stdout.write("VAPID_ADMIN_EMAIL=mailto:seu-email@mogidascruzes.sp.gov.br")