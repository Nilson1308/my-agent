from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("memory", "0004_onda2_task_due_at_interaction_undo"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserPreferences",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("telegram_user_id", models.BigIntegerField(db_index=True, unique=True)),
                (
                    "default_context",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("casa", "Casa"),
                            ("theo", "Theo"),
                            ("trabalho", "Trabalho"),
                            ("pessoal", "Pessoal"),
                        ],
                        max_length=32,
                    ),
                ),
                ("feedback_enabled", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "preferências do usuário",
                "verbose_name_plural": "preferências dos usuários",
            },
        ),
    ]