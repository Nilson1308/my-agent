from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("memory", "0006_pwa_mutation_log"),
    ]

    operations = [
        migrations.CreateModel(
            name="PwaPushSubscription",
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
                ("endpoint", models.URLField(max_length=500, unique=True)),
                ("p256dh", models.CharField(max_length=255)),
                ("auth", models.CharField(max_length=255)),
                ("user_agent", models.CharField(blank=True, max_length=255)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "verbose_name": "subscrição push PWA",
                "verbose_name_plural": "subscrições push PWA",
            },
        ),
    ]