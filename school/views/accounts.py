from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.shortcuts import get_object_or_404, redirect, render

from .. import permissions
from ..audit import log_action
from ..forms import AccountCreateForm, AccountEditForm, ForcedPasswordChangeForm
from ..models import ActivityLog, ClassAssignment, ClassRoom, Profile

LEADER_GROUP_NAME = "ClassLeader"


@permissions.head_required
def account_list(request):
    accounts = User.objects.filter(is_superuser=False).prefetch_related(
        "class_assignments__classroom"
    ).order_by("username")
    return render(request, "accounts/account_list.html", {"accounts": accounts})


@permissions.head_required
def account_create(request):
    form = AccountCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = User.objects.create_user(
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        leader_group, _ = Group.objects.get_or_create(name=LEADER_GROUP_NAME)
        user.groups.add(leader_group)
        # Profile is created automatically by signals.ensure_profile_exists (post_save),
        # already defaulting must_change_password=True — nothing to set here.

        classrooms = form.cleaned_data["classrooms"]
        for classroom in classrooms:
            ClassAssignment.objects.create(user=user, classroom=classroom)

        log_action(
            actor=request.user, action=ActivityLog.Action.CREATE, obj=user,
            new_values={"username": user.username, "classrooms": [c.name for c in classrooms]},
        )
        messages.success(request, f"አካውንት «{user.username}» ተፈጥሯል።")
        return redirect("school:account_list")

    return render(request, "accounts/account_form.html", {"form": form, "is_new": True})


@permissions.head_required
def account_edit(request, user_id):
    user = get_object_or_404(User, pk=user_id, is_superuser=False)
    current_classrooms = ClassRoom.objects.filter(assignments__user=user)

    form = AccountEditForm(
        request.POST or None,
        initial={"classrooms": current_classrooms, "is_active": user.is_active},
    )
    if request.method == "POST" and form.is_valid():
        old_values = {
            "is_active": user.is_active,
            "classrooms": [c.name for c in current_classrooms],
        }

        user.is_active = form.cleaned_data["is_active"]
        user.save(update_fields=["is_active"])

        new_classrooms = form.cleaned_data["classrooms"]
        ClassAssignment.objects.filter(user=user).exclude(classroom__in=new_classrooms).delete()
        for classroom in new_classrooms:
            ClassAssignment.objects.get_or_create(user=user, classroom=classroom)

        log_action(
            actor=request.user, action=ActivityLog.Action.UPDATE, obj=user,
            old_values=old_values,
            new_values={
                "is_active": user.is_active,
                "classrooms": [c.name for c in new_classrooms],
            },
        )
        messages.success(request, f"አካውንት «{user.username}» ተስተካክሏል።")
        return redirect("school:account_list")

    return render(request, "accounts/account_form.html", {"form": form, "is_new": False, "account": user})


@permissions.head_required
def account_reset_password(request, user_id):
    """Head sets a new password for someone else's account — no old password needed,
    same form as the forced first-login change, since the target user isn't the one
    submitting this form. Re-flags must_change_password so they're forced to pick
    their own on next login, same as a brand-new account."""
    user = get_object_or_404(User, pk=user_id, is_superuser=False)
    form = ForcedPasswordChangeForm(user=user, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.must_change_password = True
        profile.save(update_fields=["must_change_password"])

        log_action(actor=request.user, action=ActivityLog.Action.UPDATE, obj=user,
                   note=f"ኃላፊው የ«{user.username}» የይለፍ ቃል ዳግም አስጀምሯል (Head reset this account's password)")
        messages.success(request, f"የ«{user.username}» የይለፍ ቃል ተቀይሯል።")
        return redirect("school:account_list")

    return render(request, "accounts/reset_password.html", {"form": form, "account": user})