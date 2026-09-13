from datetime import timedelta

from django.conf import settings
from django.db import connection, models, transaction
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


class Problem(models.Model):
    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices)
    topic = models.CharField(max_length=100, blank=True)
    prompt = models.TextField()
    schema_sql = models.TextField(
        help_text="DDL + seed data, run inside this problem's own Postgres schema."
    )
    solution_sql = models.TextField(
        help_text="Canonical SELECT — run live to check submissions and power 'reveal solution'."
    )
    hint = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title

    @property
    def schema_name(self):
        return f"problem_{self.pk}"

    def provision_schema(self):
        """(Re)create this problem's Postgres schema from schema_sql, and
        grant the read-only practice_runner role access to it.

        Runs atomically: if schema_sql is bad, the DROP/CREATE rolls back
        too, so the schema is left exactly as it was before the call
        rather than partially provisioned.
        """
        schema = self.schema_name
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            cursor.execute(f'CREATE SCHEMA "{schema}"')
            cursor.execute(f'SET search_path TO "{schema}", public')
            cursor.execute(self.schema_sql)
            cursor.execute("SET search_path TO public")
            cursor.execute(f'GRANT USAGE ON SCHEMA "{schema}" TO practice_runner')
            cursor.execute(f'GRANT SELECT ON ALL TABLES IN SCHEMA "{schema}" TO practice_runner')
            cursor.execute(
                f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema}" '
                f"GRANT SELECT ON TABLES TO practice_runner"
            )


class Submission(models.Model):
    """One run-query attempt. 'Solved' status is derived from these —
    no separate progress table, see info/decisions/2026-09-13-mvp-scope.md.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submissions"
    )
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="submissions")
    submitted_sql = models.TextField()
    is_correct = models.BooleanField()
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        status = "correct" if self.is_correct else "incorrect"
        return f"{self.user} - {self.problem} ({status})"
