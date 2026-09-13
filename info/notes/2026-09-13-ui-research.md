# UI research: landing page, auth, dashboard

## Sources

- Google AI Overview on SQL practice platform layouts (DataLemur, StrataScratch)
- Google AI Overview on OTP email verification UX best practices, 2026
- Google AI Overview on SaaS/dev-tool landing page structure, 2026

## SQL practice platforms (DataLemur, StrataScratch)

- Question panel and editor+output panel side by side (2 or 3 column,
  resizable).
- Results area is **tabbed**, not a single static box: "Your Output" (live
  data grid, row count, runtime), "Expected Output" (target/diff, shown
  once a query has run), "Console/Errors" (syntax-highlighted error text).
- Before the first run, the output area shows an empty state with the
  schema/sample tables — matches our existing "sample tables in the UI"
  decision, just clarifies *where* that content lives.

## OTP verification UX

- Segmented 6-digit boxes, auto-submit on the last digit.
- State the destination email explicitly: "We sent a code to x@y.com".
- Visible resend cooldown (30-60s), not an always-live resend button.
- Plain-language error text ("Incorrect code, check and try again"), and
  visually/textually distinct states for wrong vs. expired vs.
  too-many-attempts.

## Landing pages for dev tools

- Hero: outcome headline + one primary CTA + a live product preview
  (screenshot/GIF of the actual editor+results), not stock art.
- Pain-point section contrasting the old way (dry tutorials/videos) with
  hands-on practice.
- 3-5 features mapped to benefits, a 3-step "how it works," FAQ.
- Skip pricing and social-proof-logo sections — don't apply to a free
  solo project with no users yet.

## Resulting page list (superset of the original 4)

1. Landing page
2. Sign up
3. Verify email (OTP) — separate screen from sign up and login
4. Login
5. Forgot password — identified gap, not designed yet
6. Problem catalog/list (filter by difficulty/topic) — identified gap,
   distinct from the per-problem workspace
7. Dashboard (per-problem workspace) — left/right split, refined below
8. Settings: profile
9. Settings: password
10. Nav shell connecting all of the above — identified gap

## Dashboard layout (refined)

- Left-top: **Hint** — collapsed by default; a second collapsible next to
  it for "Reveal Solution" (existing feature had no home in the original
  layout sketch).
- Left-bottom: query editor (syntax highlighting, Run button, Ctrl+Enter).
- Right-top: **Question** — prompt text + schema/sample-data tables shown
  inline below it.
- Right-bottom: **Results**, tabbed (Your Output / Expected Output /
  Errors) instead of one plain preview box.

## Resolved (see decisions/2026-09-13-remaining-ux-gaps.md)

- Forgot-password flow — Django's built-in password-reset views, no OTP.
- Loading/running states — inline status banner atop the Results panel
  (not a toast), three states: correct / incorrect / error.
- Empty/first-run states — no special-casing needed for 0-solved catalog;
  results panel pre-run is a plain placeholder.
- Profile settings scope — display name only in v1; email and avatar
  deferred.

## Resolved (milestone 11)

- Responsive fallback for the 2x2 dashboard split under ~768px: CSS Grid
  `grid-template-areas`, restacking to question → editor → results →
  hint → solution under `@media (max-width: 768px)`. Required refactoring
  away from the two `<div class="workspace-col">` wrapper columns from
  milestone 5, since each one bundled 3 unrelated panels and could only
  reorder as a block otherwise.
