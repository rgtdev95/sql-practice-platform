# Auth implementation: email-as-username, AllowAllUsersModelBackend

Implementation details for milestone 2, worth recording since both are
non-obvious deviations from Django's defaults that a future change could
easily "fix" back to the default and break silently.

## Email as the login identifier, without a custom user model

Per the "no custom user model" decision, `SignupForm` stores the email
address directly in `User.username` (which permits `@`/`.` by Django's
default validator) and also in `User.email`. Both signup and login forms
show a field labeled "Email"; under the hood it's still `username` as far
as Django's auth system is concerned. `EmailAuthenticationForm` (in
`practice/forms.py`) just relabels the field and overrides the
`invalid_login` error message text so it reads "email and password"
instead of Django's default "username and password".

## AllowAllUsersModelBackend instead of ModelBackend

Signup creates the `User` with `is_active=False` until the OTP is
confirmed (per
[2026-09-13-otp-email-verification.md](2026-09-13-otp-email-verification.md)).
The intended UX is: logging in before verifying shows "This account hasn't
been verified yet, [enter your code]" instead of a generic bad-credentials
error. `AuthenticationForm.confirm_login_allowed()` is Django's documented
extension point for exactly this.

**Found during testing**: with the default `ModelBackend`,
`authenticate()` itself checks `is_active` (via `user_can_authenticate()`)
and returns `None` for inactive users — so `confirm_login_allowed()` never
runs, and the form falls back to Django's generic "please enter a correct
email and password" message. This is documented Django behavior, not a
bug, but it defeats the custom messaging entirely.

**Fix**: `AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.AllowAllUsersModelBackend']`
in settings. This backend authenticates regardless of `is_active` and
leaves that check entirely to `confirm_login_allowed()` — Django's own
docs recommend it for this exact scenario. The `login()` call in
`verify_email` (practice/views.py) passes this same backend path
explicitly, since by that point `is_active` is already `True` and either
backend would work, but consistency avoids confusion later.

## Consequence

Any future auth change (e.g. adding 2FA, or a different inactive-account
policy) needs to keep this backend, or `confirm_login_allowed()` silently
stops firing for inactive users again.
