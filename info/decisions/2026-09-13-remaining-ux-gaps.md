# Remaining UX gaps: forgot-password, run states, empty states, profile scope

Resolves the open items from
[notes/2026-09-13-ui-research.md](../notes/2026-09-13-ui-research.md).

## Forgot-password flow

Use Django's built-in password-reset views unmodified:
`PasswordResetView` → emailed link with a signed, expiring token
(`default_token_generator` — no custom expiry/one-time-use code) →
`PasswordResetConfirmView` → `PasswordResetCompleteView`. Deliberately not
OTP-based — OTP stays scoped to email verification only, per
[2026-09-13-otp-email-verification.md](2026-09-13-otp-email-verification.md).
Uses the same email backend as the OTP feature.

## Loading/running states

- Run button: idle → "Running…" (disabled, spinner) while in flight.
- Result is shown as an inline status banner at the top of the Results
  panel (not a toast — avoids a second, redundant notification pattern
  alongside the already-tabbed results UI):
  - Correct → green banner, "Your Output" tab active.
  - Incorrect → amber banner, "Your Output" tab active.
  - Error (SQL exception or rejected as non-`SELECT`) → red banner,
    "Console/Errors" tab auto-selected.
- Errors are still logged as a `Submission` (`is_correct=False`,
  `error_message` populated) — no model change needed, `error_message`
  was already in the schema.

## Empty/first-run states

- Catalog with 0 solved problems: no special-case UI — the solved-badge
  rendering already degrades correctly to "nothing solved" for free.
- Results panel before the first run: plain placeholder text ("Run a query
  to see results here"). Schema/sample-data tables are not duplicated here
  — they already live in the Question panel.

## Profile settings scope (v1)

- Editable: display name only.
- Not editable in v1: email (would require re-running OTP verification —
  a real feature, deferred) and avatar (no upload/storage pipeline yet).
- Password change: Django's built-in `PasswordChangeForm` as-is.

## Consequence

No new models needed for any of these. The only new views are Django's
own built-in password-reset views (wired up, not written from scratch) and
a `ProfileUpdateView` for the single display-name field.
