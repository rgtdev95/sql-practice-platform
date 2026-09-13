import secrets

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import SignupForm, VerifyForm
from .models import EmailOTP, Problem


def home(request):
    return render(request, "home.html")


@login_required
def catalog(request):
    difficulty = request.GET.get("difficulty", "")
    topic = request.GET.get("topic", "")

    problems = Problem.objects.all()
    if difficulty:
        problems = problems.filter(difficulty=difficulty)
    if topic:
        problems = problems.filter(topic=topic)

    topics = (
        Problem.objects.exclude(topic="")
        .values_list("topic", flat=True)
        .distinct()
        .order_by("topic")
    )

    return render(
        request,
        "catalog.html",
        {
            "problems": problems,
            "topics": topics,
            "difficulties": Problem.Difficulty.choices,
            "selected_difficulty": difficulty,
            "selected_topic": topic,
        },
    )


def send_otp_email(user):
    # ponytail: no server-side resend rate limit — add one (e.g. cache-based
    # cooldown) if resend gets abused; fine for a solo/early-stage app.
    EmailOTP.objects.filter(user=user, consumed=False).delete()
    code = f"{secrets.randbelow(1_000_000):06d}"
    EmailOTP.objects.create(user=user, code=code)
    send_mail(
        subject="Your SQL Practice verification code",
        message=(
            f"Your verification code is {code}. "
            f"It expires in {EmailOTP.CODE_TTL.seconds // 60} minutes."
        ),
        from_email=None,
        recipient_list=[user.email],
    )


def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_otp_email(user)
            return redirect(f"{reverse('verify_email')}?email={user.email}")
    else:
        form = SignupForm()
    return render(request, "signup.html", {"form": form})


def verify_email(request):
    email = request.POST.get("email") or request.GET.get("email", "")

    if request.method == "POST":
        form = VerifyForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                form.add_error(None, "Account not found.")
            else:
                otp = (
                    EmailOTP.objects.filter(user=user, consumed=False)
                    .order_by("-created_at")
                    .first()
                )
                if otp is None:
                    form.add_error(None, "No active code. Request a new one below.")
                elif otp.is_expired:
                    form.add_error(None, "That code expired. Request a new one below.")
                elif otp.attempts >= EmailOTP.MAX_ATTEMPTS:
                    form.add_error(None, "Too many attempts. Request a new one below.")
                elif otp.code != form.cleaned_data["code"]:
                    otp.attempts += 1
                    otp.save(update_fields=["attempts"])
                    form.add_error("code", "Incorrect code.")
                else:
                    otp.consumed = True
                    otp.save(update_fields=["consumed"])
                    user.is_active = True
                    user.save(update_fields=["is_active"])
                    login(
                        request,
                        user,
                        backend="django.contrib.auth.backends.AllowAllUsersModelBackend",
                    )
                    return redirect("home")
    else:
        form = VerifyForm()

    return render(request, "verify_email.html", {"form": form, "email": email})


def resend_otp(request):
    if request.method == "POST":
        email = request.POST.get("email", "")
        try:
            user = User.objects.get(email__iexact=email, is_active=False)
        except User.DoesNotExist:
            pass  # don't leak whether an account exists
        else:
            send_otp_email(user)
        return redirect(f"{reverse('verify_email')}?email={email}")
    return redirect("signup")
