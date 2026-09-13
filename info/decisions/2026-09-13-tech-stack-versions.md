# Tech stack: pinned versions

## Decision

- Python 3.13.15
- uv 0.12.13
- Django 5.2.17 (LTS)
- PostgreSQL 18.6 (Docker image `postgres:18.6`)
- pgAdmin 4 9.17 (Docker image `dpage/pgadmin4:9.17`)
- Mailpit 1.31.1 (Docker image `axllent/mailpit:v1.31.1`) — local SMTP
  catcher for the email-OTP feature, replaces Django's console email
  backend as the dev stand-in (see
  [2026-09-13-otp-email-verification.md](2026-09-13-otp-email-verification.md))
- psycopg 3.3.x (`psycopg[binary]`), not psycopg2
- Docker Compose: no `version:` key — use the Compose Specification format
  bundled with current Docker Desktop
- Frontend: plain HTML/CSS/JS (`fetch`), no framework/build step

## Reasoning

- **Django 5.2 LTS over 6.1.1** (the actual latest release): 6.1 is a
  regular release with a short support window (superseded once 6.2 LTS
  ships, ~April 2027), while 5.2 LTS gets security support through
  April 2028. Fewer forced framework upgrades for a project this size.
- **Python 3.13 over 3.14**: both are supported by Django 5.2 (3.14 support
  was added in 5.2.8), but 3.13 has a year more of ecosystem/wheel maturity
  — matters for C-extension packages like psycopg.
- **PostgreSQL 18.6**: latest stable major; 19 is still in beta as of
  September 2026.
- **psycopg 3, not psycopg2**: actively developed, officially supported by
  Django since 4.2.
- **Postgres + pgAdmin run via Docker Compose**, per
  [2026-09-13-postgres-schema-sandbox.md](2026-09-13-postgres-schema-sandbox.md)
  — local dev needs a running Postgres instance; pgAdmin gives a GUI to
  inspect the `public` schema (app data) and the per-problem `problem_<id>`
  schemas directly.
- **Mailpit over Django's console email backend**: a fake SMTP server with
  a web UI (`localhost:8025`) that shows the OTP email exactly as it will
  render, instead of a plain-text dump in the terminal. One more container
  alongside Postgres/pgAdmin in the same compose file.

## Consequence

Note for Postgres 18: the official image changed its data directory to a
version-specific path (`/var/lib/postgresql/18/data`), which matters for the
`docker-compose.yml` volume mount at scaffolding time (milestone 1).
