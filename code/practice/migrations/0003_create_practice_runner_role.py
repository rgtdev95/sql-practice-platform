import os

from django.db import migrations


def create_practice_runner_role(apps, schema_editor):
    password = os.environ["PRACTICE_RUNNER_PASSWORD"]
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = %s",
            ["practice_runner"],
        )
        if cursor.fetchone() is None:
            cursor.execute(
                "CREATE ROLE practice_runner LOGIN PASSWORD %s "
                "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT",
                [password],
            )
        # Postgres-native query timeout — no manual thread/interrupt code
        # needed, unlike the superseded SQLite sandbox design.
        cursor.execute("ALTER ROLE practice_runner SET statement_timeout = '5000'")
        # practice_runner gets no access to public (auth_user, practice_*
        # tables) at all — access to problem_<id> schemas is granted
        # per-problem in Problem.provision_schema().
        cursor.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")


def reverse(apps, schema_editor):
    # Role removal isn't automated — dropping a role that owns objects
    # elsewhere on the server needs care beyond this project's scope.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("practice", "0002_problem"),
    ]

    operations = [
        migrations.RunPython(create_practice_runner_role, reverse),
    ]
