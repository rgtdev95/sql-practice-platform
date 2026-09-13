# SQL execution sandbox: Postgres, one server, per-problem schemas

Supersedes [2026-09-13-sql-execution-sandbox.md](2026-09-13-sql-execution-sandbox.md).

## Decision

Use a single PostgreSQL server for everything. Django's own data (users,
`Problem` catalog, `Submission` log) lives in the `public` schema, managed
normally through the ORM/migrations. Each practice problem's actual question
data (the tables users write queries against, e.g. `employees`,
`departments`) lives in its own Postgres schema, named `problem_<id>`,
provisioned once when the problem is authored/edited by running its stored
`schema_sql`.

User-submitted queries run through a dedicated `practice_runner` role:
`NOSUPERUSER NOCREATEDB NOCREATEROLE`, no default privileges, explicitly
granted `USAGE` + `SELECT` only on the relevant `problem_<id>` schema, with
`statement_timeout` set at the role level. The query's session does
`SET search_path TO problem_<id>` so unqualified table names resolve there
and nowhere else. This role has no access to `public` at all, so it cannot
see `auth_user` or any other app table regardless of what the query says.

Correctness is still checked by running the problem's `solution_sql` through
the same role/session and comparing result sets — unchanged from the
original decision.

## Alternatives considered

- **Postgres for app data, SQLite in-memory sandbox for questions**
  (the original decision). Rejected on revisit: once Postgres is running
  anyway for the app DB, standing up a second DB engine just for sandboxing
  is more infrastructure, not less. Schema-level isolation + a restricted
  role gives equal or better safety (real DB-level permissions instead of a
  regex-based statement filter) using the server that's already there.

- **Per-problem Postgres *database*** instead of schema. Rejected: a new
  database per problem means dynamic `CREATE DATABASE` calls and switching
  connections/catalogs per request. A schema is much lighter — same
  database, same connection, just a different `search_path` — and Postgres
  comfortably handles hundreds of schemas.

## Provisioning mechanics (add/edit a problem)

Saving a `Problem` in Django admin (`save_model`) runs:
`DROP SCHEMA IF EXISTS problem_<id> CASCADE; CREATE SCHEMA problem_<id>;`
then executes `schema_sql` inside it, then re-grants `practice_runner`.
Drop-and-recreate rather than create-once means editing a problem's
`schema_sql` and re-saving is idempotent — no leftover tables from a prior
version linger. If `schema_sql` fails (bad SQL), Django admin surfaces the
DB error as a save error; the `Problem` row is not left in a partially
provisioned state — fix the SQL and re-save to retry.

## Consequence

- Local dev needs a running Postgres instance (docker compose or local
  install) — to be wired up at scaffolding time (milestone 1).
- Problem authoring is no longer "just save a row" — saving a `Problem` in
  Django admin must also (re)provision its schema and re-grant
  `practice_runner`. This needs an admin action or a `post_save` hook.
- The schema-name-from-id derivation (`problem_<id>`) means a `Problem` must
  be saved (have a PK) before its data schema can be created — schema
  provisioning happens on save, not on model construction.
- The "show sample tables in the UI" feature reuses this exact mechanism:
  introspect `information_schema.tables` for `problem_<id>` and run
  `SELECT * FROM <table> LIMIT 20` as `practice_runner` — no separate
  storage for preview data.
