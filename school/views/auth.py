from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..audit import log_action
from ..forms import ForcedPasswordChangeForm, LoginForm, VoluntaryPasswordChangeForm
from ..models import ActivityLog, Profile


def login_view(request):
    if request.user.is_authenticated:
        return redirect("school:dashboard")

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        auth_login(request, user)
        log_action(actor=user, action=ActivityLog.Action.LOGIN, obj=user)
        # No branching on must_change_password here — ForcePasswordChangeMiddleware
        # (SRS §4.9) enforces that redirect uniformly on the very next request,
        # so this view stays a plain, ordinary login regardless of that flag.
        return redirect("school:dashboard")

    return render(request, "auth/login.html", {"form": form})


@login_required
def logout_view(request):
    auth_logout(request)
    return redirect("school:login")


@login_required
def forced_password_change_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if not profile.must_change_password:
        # Not actually pending — don't let this no-old-password-required form be
        # reachable as a way to bypass VoluntaryPasswordChangeForm's confirmation.
        return redirect("school:dashboard")

    form = ForcedPasswordChangeForm(user=request.user, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        profile.must_change_password = False
        profile.save(update_fields=["must_change_password"])
        update_session_auth_hash(request, form.user)  # keep them logged in
        log_action(actor=request.user, action=ActivityLog.Action.UPDATE, obj=request.user,
                   note="የግዴታ የይለፍ ቃል ለውጥ (forced password change)")
        messages.success(request, "የይለፍ ቃል ተቀይሯል።")
        return redirect("school:dashboard")

    return render(request, "auth/force_password_change.html", {"form": form})


@login_required
def password_change_view(request):
    form = VoluntaryPasswordChangeForm(user=request.user, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        update_session_auth_hash(request, form.user)
        log_action(actor=request.user, action=ActivityLog.Action.UPDATE, obj=request.user,
                   note="የይለፍ ቃል ለውጥ (voluntary password change)")
        messages.success(request, "የይለፍ ቃል ተቀይሯል።")
        return redirect("school:profile")

    return render(request, "auth/password_change.html", {"form": form})


@login_required
def profile_view(request):
    return render(request, "auth/profile.html", {"account": request.user})