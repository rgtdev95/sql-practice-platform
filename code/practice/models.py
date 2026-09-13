from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class EmailOTP(models.Model):
    """One-time code proving a signup's email address is real.

    Not used for login or password reset — see
    info/decisions/2026-09-13-otp-email-verification.md.
    """

    CODE_TTL = timedelta(minutes=10)
    MAX_ATTEMPTS = 5

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_otps"
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed = models.BooleanField(default=False)

    @property
    def is_expired(self):
        return timezone.now() > self.created_at + self.CODE_TTL

    def __str__(self):
        return f"OTP for {self.user.email} ({'consumed' if self.consumed else 'active'})"
