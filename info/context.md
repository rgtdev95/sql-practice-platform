# Context

## What this is

A user-friendly web platform for practicing SQL: users browse a catalog of
problems, write queries in a browser-based editor against a per-problem
sandboxed dataset, and get instant correct/incorrect feedback.

## Current status

Planning stage — no code written yet. Stack, MVP scope, and database
architecture decided (see decisions/). Next step: scaffold the uv + Django
project (milestone 1), including a local Postgres instance.

Planned milestones:
1. uv + Django scaffold, base template, local Postgres + pgAdmin + Mailpit
   via docker compose
2. Auth: sign up, email OTP verification, login, logout, forgot-password
   (Django built-in auth + password-reset views + an `EmailOTP` model
   gating `is_active`)
3. `Problem` model + Django admin, with schema provisioning
   (`problem_<id>` Postgres schema) wired into save
4. Problem catalog page (filter by difficulty/topic) + nav shell
5. Dashboard (per-problem workspace): question + schema panel, query
   editor, tabbed results (Your Output / Expected Output / Errors), with
   sample-data tables rendered from `information_schema` introspection
6. Sandboxed SQL execution via the `practice_runner` Postgres role, safety
   checks
7. Run-query AJAX endpoint + JS results table, with Running/Correct/
   Incorrect/Error states shown as an inline banner on the Results panel
8. Submission tracking + solved badges
9. Hints + reveal-solution UI (left panel of the dashboard)
10. Profile (display name only) + password settings pages
11. CSS polish, responsive fallback for the dashboard split below ~768px
    (still open — see notes/2026-09-13-ui-research.md)

See [notes/2026-09-13-ui-research.md](notes/2026-09-13-ui-research.md) for
the full page list and layout research,
[decisions/2026-09-13-otp-email-verification.md](decisions/2026-09-13-otp-email-verification.md)
for the auth scope decision, and
[decisions/2026-09-13-remaining-ux-gaps.md](decisions/2026-09-13-remaining-ux-gaps.md)
for forgot-password/run-states/empty-states/profile-scope decisions.

## Project structure

Planned scaffold (milestone 1, not built yet). All code lives under `code/`,
kept separate from `info/` (project docs) and repo-root files:

```
sql-practice-platform/
├── CLAUDE.md
├── info/                  # this folder — docs, decisions, diagrams
└── code/                  # everything that runs
    ├── pyproject.toml     # uv-managed deps: django, psycopg[binary], sqlparse
    ├── uv.lock
    ├── docker-compose.yml # postgres:18.6 + pgadmin4:9.17 + mailpit:v1.31.1
    ├── .env               # DB creds, SECRET_KEY (git-ignored)
    ├── manage.py
    ├── config/            # Django project package
    │   ├── settings.py    # DATABASES pointed at the compose Postgres
    │   └── urls.py
    ├── practice/          # the one Django app (models, views, admin)
    ├── templates/
    │   └── base.html      # shared page shell (nav, css link)
    └── static/
        └── css/base.css
```

One Django app (`practice`) per the app-per-project convention below — no
`accounts`/`problems`/`submissions` split at this size.

## Conventions

- **Tech stack** (pinned versions in
  [decisions/2026-09-13-tech-stack-versions.md](decisions/2026-09-13-tech-stack-versions.md)):
  Python 3.13.15, uv 0.12.13, Django 5.2.17 LTS, PostgreSQL 18.6 + pgAdmin
  4 9.17 + Mailpit 1.31.1 (all via Docker Compose), psycopg 3.3.x.
  Server-rendered templates + vanilla JS (fetch) for interactivity. No DRF,
  no SPA framework.
- **One Django app** (`practice`) — don't split into multiple apps at this size.
- **Django admin is the content-authoring tool** for problems — no custom CMS.
- **"Solved" status is derived**, not stored — query `Submission` for distinct
  correct problems per user rather than maintaining a separate progress table.
- **Expected results are computed live** by running each problem's
  `solution_sql` against the same schema/role as the user's query, not
  stored as a precomputed blob — nothing to keep in sync when problem data
  changes.
- **Database**: a single PostgreSQL server, two tiers:
  - `public` schema — Django-managed app data (`auth_user`, `EmailOTP`,
    `practice_problem`, `practice_submission`).
  - one Postgres schema per problem (`problem_<id>`) holding that problem's
    actual question tables/data, provisioned once at problem-authoring time.
  - User-submitted SQL runs through a locked-down `practice_runner` role
    (SELECT-only, scoped to one `problem_<id>` schema via `search_path`,
    `statement_timeout` set at the role level, zero access to `public`).
  - The "sample tables in the UI" feature reuses the same mechanism:
    introspect `information_schema.tables` for `problem_<id>` and
    `SELECT ... LIMIT 20` as `practice_runner`.
  - See [decisions/2026-09-13-postgres-schema-sandbox.md](decisions/2026-09-13-postgres-schema-sandbox.md)
    (supersedes the original SQLite-sandbox decision).
- Deployment target is not yet decided — out of scope until the app works
  locally. Local dev needs a running Postgres instance.
