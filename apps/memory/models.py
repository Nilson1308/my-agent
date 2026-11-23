from django.db import models
from pgvector.django import VectorField

EMBEDDING_DIMENSIONS = 384


class DomainContext(models.TextChoices):
    CASA = "casa", "Casa"
    THEO = "theo", "Theo"
    TRABALHO = "trabalho", "Trabalho"
    PESSOAL = "pessoal", "Pessoal"


class TaskStatus(models.TextChoices):
    PENDING = "pending", "Pendente"
    DONE = "done", "Concluída"


class InputType(models.TextChoices):
    TEXT = "text", "Texto"
    AUDIO = "audio", "Áudio"


class ShoppingItem(models.Model):
    name = models.CharField(max_length=255)
    quantity = models.CharField(max_length=64, blank=True)
    is_bought = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    bought_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "item de mercado"
        verbose_name_plural = "itens de mercado"
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(is_bought=False),
                name="uniq_shopping_pending_name",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Task(models.Model):
    title = models.CharField(max_length=512)
    context = models.CharField(max_length=32, choices=DomainContext.choices)
    due_date = models.DateField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date", "-created_at"]
        verbose_name = "tarefa"
        verbose_name_plural = "tarefas"

    def __str__(self) -> str:
        return self.title


class Event(models.Model):
    title = models.CharField(max_length=512)
    context = models.CharField(max_length=32, choices=DomainContext.choices)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    reminded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_at"]
        verbose_name = "compromisso"
        verbose_name_plural = "compromissos"

    def __str__(self) -> str:
        return self.title


class Reminder(models.Model):
    title = models.CharField(max_length=512)
    message = models.TextField(blank=True)
    context = models.CharField(max_length=32, choices=DomainContext.choices, default=DomainContext.PESSOAL)
    remind_at = models.DateTimeField()
    reminded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["remind_at"]
        verbose_name = "lembrete agendado"
        verbose_name_plural = "lembretes agendados"

    def __str__(self) -> str:
        return f"{self.title} @ {self.remind_at:%d/%m %H:%M}"


class PwaPushSubscription(models.Model):
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "subscrição push PWA"
        verbose_name_plural = "subscrições push PWA"

    def __str__(self) -> str:
        return self.endpoint[:64]


class PwaMutationLog(models.Model):
    action = models.CharField(max_length=64, db_index=True)
    target_type = models.CharField(max_length=32, blank=True)
    target_id = models.BigIntegerField(null=True, blank=True)
    client_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "log mutação PWA"
        verbose_name_plural = "logs mutações PWA"


class UserPreferences(models.Model):
    telegram_user_id = models.BigIntegerField(unique=True, db_index=True)
    default_context = models.CharField(
        max_length=32,
        choices=DomainContext.choices,
        blank=True,
    )
    feedback_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "preferências do usuário"
        verbose_name_plural = "preferências dos usuários"

    def __str__(self) -> str:
        return f"prefs:{self.telegram_user_id}"


class PendingConfirmation(models.Model):
    telegram_user_id = models.BigIntegerField(db_index=True)
    action_type = models.CharField(max_length=32)
    payload_json = models.JSONField()
    prompt_message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "confirmação pendente"
        verbose_name_plural = "confirmações pendentes"


class Note(models.Model):
    content = models.TextField()
    context = models.CharField(max_length=32, choices=DomainContext.choices)
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "nota"
        verbose_name_plural = "notas"

    def __str__(self) -> str:
        preview = self.content[:60]
        if len(self.content) > 60:
            preview += "…"
        return preview


class InteractionLog(models.Model):
    raw_input = models.TextField()
    input_type = models.CharField(max_length=16, choices=InputType.choices)
    parsed_json = models.JSONField(null=True, blank=True)
    bot_response = models.TextField(blank=True)
    llm_outcome = models.CharField(max_length=24, blank=True, default="")
    telegram_user_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    effects_json = models.JSONField(default=list, blank=True)
    user_feedback = models.SmallIntegerField(
        null=True,
        blank=True,
        choices=[(1, "Bom"), (-1, "Ruim")],
    )
    undone_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "log de interação"
        verbose_name_plural = "logs de interação"

    def __str__(self) -> str:
        return f"{self.input_type} @ {self.created_at:%Y-%m-%d %H:%M}"