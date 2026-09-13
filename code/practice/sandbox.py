"""Read-only access to a problem's own Postgres schema, via the
practice_runner role — see info/decisions/2026-09-13-postgres-schema-sandbox.md.

This module is the one place that opens a connection as practice_runner.
Milestone 5 uses it only for the sample-table preview; milestone 6 will add
running a submitted query the same way.
"""

import os

import psycopg


def runner_connection():
    return psycopg.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        dbname=os.environ["POSTGRES_DB"],
        user="practice_runner",
        password=os.environ["PRACTICE_RUNNER_PASSWORD"],
    )


def get_sample_tables(problem, limit=20):
    """[{name, columns, rows}, ...] for every table in the problem's
    schema, read the same way a submitted query eventually will be."""
    tables = []
    with runner_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = %s ORDER BY table_name",
            [problem.schema_name],
        )
        table_names = [row[0] for row in cur.fetchall()]
        for name in table_names:
            cur.execute(f'SELECT * FROM "{problem.schema_name}"."{name}" LIMIT {int(limit)}')
            columns = [desc.name for desc in cur.description]
            rows = cur.fetchall()
            tables.append({"name": name, "columns": columns, "rows": rows})
    return tables
