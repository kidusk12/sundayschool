from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .. import permissions, registry, services
from ..forms import RemovalRequestForm
from ..models import (
    AttendanceRow,
    AttendanceSheet,
    Mark,
    MarkList,
    RemovalRequest,
    Student,
    StudentFile,
)

# URL-friendly slugs -> the real model classes, matching registry.REMOVABLE_REGISTRY's keys.
KIND_MODELS = {
    "student": Student,
    "sheet": AttendanceSheet,
    "row": AttendanceRow,
    "marklist": MarkList,
    "mark": Mark,
    "file": StudentFile,
}


@login_required
def request_removal(request, kind, object_id):
    """Any staff member (not just Head) can reach this — but only for an
    object in a class they can actually access (checked below), and only for
    a kind registry.py actually allows removing (SRS §4.7)."""
    model = KIND_MODELS.get(kind)
    if model is None:
        return render(request, "removal/not_removable.html", status=404)

    target = get_object_or_404(model, pk=object_id)
    classroom = registry.get_classroom_for(target)
    if not permissions.can_access_classroom(request.user, classroom):
        return render(request, "removal/not_removable.html", status=403)

    form = RemovalRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        services.file_removal_request(
            target=target, reason=form.cleaned_data["reason"], user=request.user
        )
        return redirect("school:class_detail", classroom_id=classroom.pk)

    return render(request, "removal/request_form.html", {
        "form": form,
        "target": target,
        "label": registry.get_label_for(target),
        "classroom": classroom,
    })


@permissions.head_required
def pending_list(request):
    requests = RemovalRequest.objects.filter(
        status=RemovalRequest.Status.PENDING
    ).select_related("classroom", "requested_by").order_by("requested_at")
    return render(request, "removal/pending_list.html", {"requests": requests})


@permissions.head_required
def resolve(request, request_id):
    removal_request = get_object_or_404(
        RemovalRequest, pk=request_id, status=RemovalRequest.Status.PENDING
    )
    if request.method == "POST":
        approve = request.POST.get("action") == "delete"
        services.resolve_removal_request(
            request=removal_request, approve=approve, user=request.user
        )
        return redirect("school:removal_pending_list")

    return render(request, "removal/resolve_confirm.html", {"removal_request": removal_request})