# Generated manually for roadmap item 9/11

from django.db import migrations, models


def dedupe_pending_shopping_names(apps, schema_editor):
    ShoppingItem = apps.get_model("memory", "ShoppingItem")
    seen: set[str] = set()
    for item in ShoppingItem.objects.filter(is_bought=False).order_by("created_at", "id"):
        key = item.name.strip().lower()
        if key in seen:
            item.delete()
        else:
            seen.add(key)


class Migration(migrations.Migration):

    dependencies = [
        ("memory", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="interactionlog",
            name="llm_outcome",
            field=models.CharField(blank=True, default="", max_length=24),
        ),
        migrations.RunPython(dedupe_pending_shopping_names, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="shoppingitem",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_bought", False)),
                fields=("name",),
                name="uniq_shopping_pending_name",
            ),
        ),
    ]