> **Superseded 2026-09-13** by
> [2026-09-13-postgres-schema-sandbox.md](2026-09-13-postgres-schema-sandbox.md)
> — the project moved to Postgres for the app DB, and it turned out reusing
> the same server for sandboxing (via per-problem schemas + a locked-down
> role) is simpler than running two DB engines. Kept for history.

# SQL execution sandbox: per-problem in-memory SQLite (superseded)

## Decision

Each practice problem stores its own `schema_sql` (CREATE TABLE + seed data).
Every query run creates a fresh `sqlite3.connect(":memory:")`, replays
`schema_sql` into it, then executes the user's query against it. Only a
single `SELECT` statement is allowed through (checked before execution).
Correctness is checked by running the problem's `solution_sql` against the
same fresh DB and comparing result sets, not by storing a precomputed
expected-result blob.

## Alternatives considered

- **Shared PostgreSQL with per-problem schemas + a locked-down read-only
  role.** Closer to "real" SQL (window functions, stricter typing, richer
  error messages) and more realistic for advanced problems. Rejected for
  v1 because it requires a running DB server, connection pooling, and a
  read-only role/permissions setup to build and maintain before there's
  even a working core loop. Revisit if problem content needs Postgres-only
  features SQLite can't express.

- **Precomputed expected-result JSON per problem**, checked by admins at
  authoring time instead of computed live. Rejected: it can silently drift
  from `schema_sql` if seed data is ever edited, and living solution_sql is
  needed anyway for the "reveal solution" feature, so running it live costs
  nothing extra.

## Why in-memory SQLite

- Zero extra infrastructure — no DB server to run, pool, or secure.
- Trivial to reset: a new DB per query run means no state ever leaks
  between users or between attempts.
- SQLite has no network stack, users, or file-system access surface from
  inside a query, so the safety burden is just "block non-SELECT
  statements" and "kill long-running queries" (via `connection.interrupt()`
  on a timer) rather than a full permissions model.

## Consequence

The sandbox runner is on the money path (arbitrary user-submitted SQL) and
needs its own test coverage: allowed SELECT succeeds, non-SELECT statements
are rejected, and a long-running query gets interrupted rather than hanging
the request.
