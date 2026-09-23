from django.db import migrations


def replace_separators(apps, schema_editor):
    SKU = apps.get_model("crm", "SKU")
    manager = SKU.objects.using(schema_editor.connection.alias)
    rows = list(manager.values("pk", "display_name_cn"))
    names = {}
    updates = []
    for row in rows:
        original = row["display_name_cn"] or ""
        name = original.replace("|", "-")
        key = " ".join(name.casefold().strip().split())
        if key and key in names:
            raise RuntimeError(f"SKU name separator conversion conflicts: {names[key]} / {row['pk']}")
        if key:
            names[key] = row["pk"]
        if name != original:
            updates.append((row["pk"], name, key or None))
    # Clear keys first so the uniqueness constraint also permits key swaps.
    manager.filter(pk__in=[pk for pk, _, _ in updates]).update(display_name_key=None)
    for pk, name, key in updates:
        manager.filter(pk=pk).update(display_name_cn=name, display_name_key=key)


class Migration(migrations.Migration):
    dependencies = [("crm", "0056_purchase_source_characteristics_snapshot")]
    operations = [migrations.RunPython(replace_separators, migrations.RunPython.noop)]
