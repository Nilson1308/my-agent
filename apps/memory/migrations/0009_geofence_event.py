from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("memory", "0008_interactionlog_channel"),
    ]

    operations = [
        migrations.CreateModel(
            name="GeofenceEvent",
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
                ("location_label", models.CharField(blank=True, max_length=128)),
                ("latitude", models.FloatField(blank=True, null=True)),
                ("longitude", models.FloatField(blank=True, null=True)),
                ("client_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("status", models.CharField(db_index=True, max_length=24)),
                ("items_count", models.PositiveIntegerField(default=0)),
                ("telegram_sent", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "verbose_name": "evento geofence",
                "verbose_name_plural": "eventos geofence",
            },
        ),
    ]