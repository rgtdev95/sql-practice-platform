"""Read-only access to a problem's own Postgres schema, via the
practice_runner role — see info/decisions/2026-09-13-postgres-schema-sandbox.md.

This module is the one place that opens a connection as practice_runner.
"""

import os

import psycopg
import sqlparse
from django.db import connection as django_connection


class QueryError(Exception):
    """A submitted query was rejected, errored, or timed out."""


def runner_connection():
    # Derive host/port/dbname from Django's own live connection rather than
    # POSTGRES_* env vars directly, so this automatically follows Django to
    # whatever database it's actually using — notably the separate
    # test_<name> database Django's test runner switches to, which the env
    # vars never change.
    settings_dict = django_connection.settings_dict
    return psycopg.connect(
        host=settings_dict["HOST"],
        port=settings_dict["PORT"],
        dbname=settings_dict["NAME"],
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


def validate_select_only(sql):
    """Reject anything but a single read-only statement.

    This is defense in depth, not the real safety boundary — practice_runner
    itself has no write privileges anywhere, so a rejected statement would
    fail at the database level regardless. This just turns that into a
    clean error before wasting a query round-trip.
    """
    statements = [s for s in sqlparse.parse(sql) if s.token_first(skip_cm=True) is not None]
    if len(statements) != 1:
        raise QueryError("Only a single SELECT statement is allowed.")
    first_token = statements[0].token_first(skip_cm=True)
    if first_token is None or first_token.value.upper() not in ("SELECT", "WITH"):
        raise QueryError("Only SELECT queries are allowed.")


def run_in_schema(problem, sql):
    """Run one read-only statement against a problem's schema as
    practice_runner. Returns (columns, rows); raises QueryError on
    rejected input, timeout, or any other database error."""
    validate_select_only(sql)
    try:
        with runner_connection() as conn, conn.cursor() as cur:
            cur.execute(f'SET search_path TO "{problem.schema_name}"')
            cur.execute(sql)
            columns = [desc.name for desc in cur.description]
            rows = cur.fetchall()
            return columns, rows
    except psycopg.errors.QueryCanceled:
        raise QueryError("Query took too long and was cancelled.")
    except psycopg.Error as e:
        raise QueryError(str(e).strip())


def check_submission(problem, sql):
    """Run a submitted query and compare it against the problem's own
    solution_sql, run live the same way (see decisions/2026-09-13-postgres-
    schema-sandbox.md — nothing to keep in sync when problem data changes).

    Returns {"status": "correct" | "incorrect" | "error", ...}.
    """
    try:
        columns, rows = run_in_schema(problem, sql)
    except QueryError as e:
        return {"status": "error", "error": str(e)}

    expected_columns, expected_rows = run_in_schema(problem, problem.solution_sql)

    # Order matters only if the problem's own solution asks for it — not
    # whether the *submission* happens to add an ORDER BY. Whether row
    # order is part of "correct" is the problem author's call.
    if "order by" in problem.solution_sql.lower():
        is_correct = rows == expected_rows
    else:
        is_correct = sorted(rows, key=repr) == sorted(expected_rows, key=repr)

    return {
        "status": "correct" if is_correct else "incorrect",
        "columns": columns,
        "rows": rows,
        "expected_columns": expected_columns,
        "expected_rows": expected_rows,
    }
