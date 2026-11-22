from django.contrib import admin

from apps.memory.models import Event, InteractionLog, Note, ShoppingItem, Task


@admin.register(ShoppingItem)
class ShoppingItemAdmin(admin.ModelAdmin):
    list_display = ("name", "quantity", "is_bought", "created_at", "bought_at")
    list_filter = ("is_bought",)
    search_fields = ("name",)
    ordering = ("-created_at",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "context", "status", "due_date", "created_at")
    list_filter = ("context", "status", "due_date")
    search_fields = ("title",)
    ordering = ("due_date", "-created_at")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "context", "start_at", "end_at", "reminded", "created_at")
    list_filter = ("context", "reminded", "start_at")
    search_fields = ("title",)
    ordering = ("start_at",)


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("content_preview", "context", "has_embedding", "created_at")
    list_filter = ("context",)
    search_fields = ("content",)
    ordering = ("-created_at",)

    @admin.display(description="Conteúdo")
    def content_preview(self, obj: Note) -> str:
        preview = obj.content[:80]
        if len(obj.content) > 80:
            preview += "…"
        return preview

    @admin.display(boolean=True, description="Embedding")
    def has_embedding(self, obj: Note) -> bool:
        return obj.embedding is not None


@admin.register(InteractionLog)
class InteractionLogAdmin(admin.ModelAdmin):
    list_display = ("id", "input_type", "created_at", "response_preview")
    list_filter = ("input_type", "created_at")
    search_fields = ("raw_input", "bot_response")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    @admin.display(description="Resposta")
    def response_preview(self, obj: InteractionLog) -> str:
        preview = obj.bot_response[:80]
        if len(obj.bot_response) > 80:
            preview += "…"
        return preview or "—"