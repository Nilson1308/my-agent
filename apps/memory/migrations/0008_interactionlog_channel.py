from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("memory", "0007_pwa_push_subscription"),
    ]

    operations = [
        migrations.AddField(
            model_name="interactionlog",
            name="channel",
            field=models.CharField(
                choices=[("telegram", "Telegram"), ("pwa", "PWA")],
                db_index=True,
                default="telegram",
                max_length=16,
            ),
        ),
    ]