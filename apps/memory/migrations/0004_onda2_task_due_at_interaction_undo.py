# Generated manually — Onda 2

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("memory", "0003_task_completed_reminder_confirmation"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="due_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="interactionlog",
            name="telegram_user_id",
            field=models.BigIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="interactionlog",
            name="effects_json",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="interactionlog",
            name="user_feedback",
            field=models.SmallIntegerField(
                blank=True,
                choices=[(-1, "Ruim"), (1, "Bom")],
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="interactionlog",
            name="undone_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]