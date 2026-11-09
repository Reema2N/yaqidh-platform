from django.db import migrations


def create_cameras_table(apps, schema_editor):
    """Create the `cameras` table on a fresh database; skip it if it already exists."""
    Cameras = apps.get_model('live_monitoring', 'cameras')
    table = Cameras._meta.db_table
    existing = schema_editor.connection.introspection.table_names()
    if table not in existing:
        schema_editor.create_model(Cameras)


class Migration(migrations.Migration):

    dependencies = [
        ('live_monitoring', '0002_cameras_delete_camera'),
    ]

    operations = [
        migrations.RunPython(create_cameras_table, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name='cameras',
            options={'managed': True},
        ),
    ]
