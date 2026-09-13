# Context

## What this is

A user-friendly web platform for practicing SQL: users browse a catalog of
problems, write queries in a browser-based editor against a per-problem
sandboxed dataset, and get instant correct/incorrect feedback.

## Current status

Milestones 1-4 are done. `code/` has a working Django project wired to real
Postgres, with pgAdmin and Mailpit running alongside it via Docker Compose,
a fully working auth flow (sign up, email-OTP verification, login, logout,
forgot-password), `Problem` authoring via Django admin with real
per-problem Postgres schema provisioning, and a login-gated problem catalog
page (filterable by difficulty/topic) linked from the nav. All tested end
to end against the running dev server and real Postgres — including
confirming `practice_runner` can read a problem's own schema but gets
`permission denied` on `public.auth_user`. Next step: milestone 5
(dashboard/workspace shell).

To run it: `docker compose up -d` (from `code/`), then
`uv run manage.py runserver`. pgAdmin is on **5051**, not 5050 — that port
was already taken by an unrelated project on this machine. Mailpit's inbox
is at `localhost:8025`.

Deviations from the original plan: `uv init` defaulted to a
distributable-library layout (`src/`, a build-system, an entry-point
script) — stripped, since a Django app isn't a published package
(`tool.uv.package = false` instead). pgAdmin's host port is 5051 (see
above). Auth needed one non-obvious fix — Django's default `ModelBackend`
silently blocks inactive users before the custom "please verify your
email" message can run; switched to `AllowAllUsersModelBackend`, see
[decisions/2026-09-13-auth-implementation.md](decisions/2026-09-13-auth-implementation.md).
The `practice_runner` Postgres role is created by a hand-written migration
(`practice/migrations/0003_create_practice_runner_role.py`), not a
management command — ties its creation to `migrate`, which already needs
to run before the app works.

Planned milestones:
1. ~~uv + Django scaffold, base template, local Postgres + pgAdmin +
   Mailpit via docker compose~~ — done
2. ~~Auth: sign up, email OTP verification, login, logout,
   forgot-password~~ — done
3. ~~`Problem` model + Django admin, with schema provisioning
   (`problem_<id>` Postgres schema) wired into save~~ — done
4. ~~Problem catalog page (filter by difficulty/topic) + nav shell~~ — done
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

Built (milestone 1). All code lives under `code/`, kept separate from
`info/` (project docs) and repo-root files:

```
sql-practice-platform/
├── CLAUDE.md
├── info/                  # this folder — docs, decisions, diagrams
└── code/                  # everything that runs
    ├── pyproject.toml     # uv-managed deps: django, psycopg[binary], sqlparse
    ├── uv.lock
    ├── docker-compose.yml # postgres:18.6 + pgadmin4:9.17 + mailpit:v1.31.1
    ├── .env               # DB creds, SECRET_KEY (git-ignored)
    ├── .env.example
    ├── manage.py
    ├── config/            # Django project package
    │   ├── settings.py    # env-driven: Postgres, Mailpit SMTP, auth backend, templates/static dirs
    │   └── urls.py        # home, problems, signup/verify/resend, login/logout, password-reset
    ├── practice/          # the one Django app
    │   ├── models.py      # EmailOTP, Problem (+ provision_schema)
    │   ├── forms.py        # SignupForm, VerifyForm, EmailAuthenticationForm
    │   ├── views.py
    │   ├── admin.py        # ProblemAdmin wires provision_schema() into save
    │   ├── tests.py         # provisioning: grants, idempotency, rollback-on-bad-SQL
    │   └── migrations/
    │       └── 0003_create_practice_runner_role.py
    ├── templates/
    │   ├── base.html      # shared page shell (nav shows auth state)
    │   ├── home.html
    │   ├── catalog.html
    │   ├── signup.html
    │   ├── verify_email.html
    │   └── registration/  # Django auth views' default template location
    │       ├── login.html
    │       └── password_reset_*.html
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
