from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("memory", "0005_user_preferences_pwa"),
    ]

    operations = [
        migrations.CreateModel(
            name="PwaMutationLog",
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
                ("action", models.CharField(db_index=True, max_length=64)),
                ("target_type", models.CharField(blank=True, max_length=32)),
                ("target_id", models.BigIntegerField(blank=True, null=True)),
                ("client_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "verbose_name": "log mutação PWA",
                "verbose_name_plural": "logs mutações PWA",
            },
        ),
    ]