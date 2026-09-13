# Auth: OTP for email verification only

## Decision

Sign up collects email + password as normal. Immediately after signup, a
6-digit OTP is emailed and must be entered to activate the account. Login
afterward is plain email + password — no OTP involved. Forgot-password is a
separate, simpler flow (not built yet) and does not need to reuse the OTP
mechanism.

## Alternatives considered

- **OTP also used for password reset** (reuse the same verify-code flow
  instead of a reset link). Not chosen for v1 — keeping OTP to exactly one
  purpose (prove you own this email address once) keeps the first auth
  build small. Can extend to this later without changing the OTP mechanism
  itself.
- **OTP as a second factor on every login.** Rejected: meaningfully bigger
  scope (rate-limiting, resend UX, extra email volume on every login) for a
  solo/early-stage practice platform where the main risk being mitigated is
  "did this email address actually go to the account owner," which one-time
  verification already covers.

## Consequence

- Django's `User.is_active` (or a dedicated `is_verified` flag) gates
  login until the OTP is confirmed.
- Needs an `EmailOTP` record (user FK, code, expires_at, attempts) and an
  outgoing email backend. For local dev, Django's `EMAIL_BACKEND` points at
  Mailpit (SMTP on port 1025, web UI on `localhost:8025`) — a Docker
  Compose service alongside Postgres/pgAdmin, see
  [2026-09-13-tech-stack-versions.md](2026-09-13-tech-stack-versions.md).
  A real provider is still an open deployment decision, out of scope for now.
- UI needs a dedicated "Verify your email" screen (see
  [../notes/2026-09-13-ui-research.md](../notes/2026-09-13-ui-research.md)
  for the interaction details: segmented input, resend cooldown, plain-
  language error states) — separate from both the signup form and login.
- Forgot-password is now a known gap, not yet designed — tracked in the UI
  research notes.
