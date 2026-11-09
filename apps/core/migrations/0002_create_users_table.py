from django.db import migrations


def create_users_table(apps, schema_editor):
    """
    The `users` table is unmanaged (it is shared with the rest of the system),
    so Django never creates it. On a fresh database we create it here; on an
    existing database this does nothing.
    """
    Users = apps.get_model('core', 'Users')
    table = Users._meta.db_table
    existing = schema_editor.connection.introspection.table_names()
    if table not in existing:
        schema_editor.create_model(Users)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_users_table, migrations.RunPython.noop),
    ]
