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

    def __str__(self) -> str:
        return self.name


class Task(models.Model):
    title = models.CharField(max_length=512)
    context = models.CharField(max_length=32, choices=DomainContext.choices)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
    )
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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "log de interação"
        verbose_name_plural = "logs de interação"

    def __str__(self) -> str:
        return f"{self.input_type} @ {self.created_at:%Y-%m-%d %H:%M}"