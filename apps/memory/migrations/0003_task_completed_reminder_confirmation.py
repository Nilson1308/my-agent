# Generated manually — conclusão de tarefas, lembretes e confirmações

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("memory", "0002_llm_outcome_shopping_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="Reminder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=512)),
                ("message", models.TextField(blank=True)),
                (
                    "context",
                    models.CharField(
                        choices=[
                            ("casa", "Casa"),
                            ("theo", "Theo"),
                            ("trabalho", "Trabalho"),
                            ("pessoal", "Pessoal"),
                        ],
                        default="pessoal",
                        max_length=32,
                    ),
                ),
                ("remind_at", models.DateTimeField()),
                ("reminded", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "lembrete agendado",
                "verbose_name_plural": "lembretes agendados",
                "ordering": ["remind_at"],
            },
        ),
        migrations.CreateModel(
            name="PendingConfirmation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("telegram_user_id", models.BigIntegerField(db_index=True)),
                ("action_type", models.CharField(max_length=32)),
                ("payload_json", models.JSONField()),
                ("prompt_message", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
            ],
            options={
                "verbose_name": "confirmação pendente",
                "verbose_name_plural": "confirmações pendentes",
                "ordering": ["-created_at"],
            },
        ),
    ]