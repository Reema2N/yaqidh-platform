from django.db import migrations


def ensure_violence_events_table(apps, schema_editor):
    """
    Migration 0003 creates `violence_events` and then deletes the old
    `ViolenceEvents` model, which points at the same table name. On a fresh
    database that drops the table again, so we re-create it here if missing.
    Existing databases (where the detection pipeline already writes to the
    table) are left untouched.
    """
    Event = apps.get_model('incidents', 'violence_events')
    table = Event._meta.db_table
    existing = schema_editor.connection.introspection.table_names()
    if table not in existing:
        schema_editor.create_model(Event)


class Migration(migrations.Migration):

    dependencies = [
        ('incidents', '0003_violence_events_delete_violenceevents'),
    ]

    operations = [
        migrations.RunPython(ensure_violence_events_table, migrations.RunPython.noop),
    ]
