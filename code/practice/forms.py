from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.safestring import mark_safe


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email",)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                mark_safe(
                    "An account with this email already exists. If you "
                    "haven't verified it yet, "
                    f'<a href="{reverse("verify_email")}?email={email}">'
                    "enter your code</a> or request a new one there."
                )
            )
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        user.is_active = False
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name"]
        labels = {"first_name": "Display name"}


class VerifyForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        label="Verification code",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "one-time-code"}),
    )


class EmailAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": (
            "Please enter a correct email and password. Note that both "
            "fields may be case-sensitive."
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Email"

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(
                mark_safe(
                    "This account hasn't been verified yet. "
                    f'<a href="{reverse("verify_email")}?email={user.email}">'
                    "enter your code</a> or request a new one there."
                ),
                code="inactive",
            )
