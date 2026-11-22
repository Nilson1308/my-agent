from django.core.management.base import BaseCommand

from apps.memory.tasks import build_morning_briefing_message, send_morning_briefing


class Command(BaseCommand):
    help = "Dispara o briefing matinal agora (Telegram + preview no terminal)."

    def handle(self, *args, **options):
        message = build_morning_briefing_message()
        self.stdout.write(self.style.HTTP_INFO("=== Mensagem do briefing ==="))
        self.stdout.write(message)
        self.stdout.write("")

        result = send_morning_briefing()
        sent = result.get("sent")
        if sent:
            self.stdout.write(self.style.SUCCESS("Briefing enviado no Telegram."))
        else:
            self.stdout.write(
                self.style.WARNING("Falha ao enviar no Telegram (verifique TOKEN/CHAT_ID).")
            )