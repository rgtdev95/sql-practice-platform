from django.contrib import admin

from .models import EmailOTP, Problem


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "code", "created_at", "attempts", "consumed")
    list_filter = ("consumed",)


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "difficulty", "topic", "created_at")
    list_filter = ("difficulty", "topic")
    prepopulated_fields = {"slug": ("title",)}

    def save_model(self, request, obj, form, change):
        # ponytail: a bad schema_sql surfaces as Django's debug error page
        # (clear enough solo, since you're the only admin) rather than a
        # polished inline form error — upgrade to a clean()-time dry-run
        # validation if this ever needs to be smoother.
        super().save_model(request, obj, form, change)
        obj.provision_schema()
