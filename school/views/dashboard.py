from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .. import permissions
from ..models import ClassRoom, RemovalRequest, Student


@login_required
def dashboard_view(request):
    if permissions.is_head(request.user):
        context = {
            "class_count": ClassRoom.objects.filter(is_active=True).count(),
            "student_count": Student.objects.count(),
            "pending_removal_count": RemovalRequest.objects.filter(
                status=RemovalRequest.Status.PENDING
            ).count(),
        }
        return render(request, "dashboard/head_dashboard.html", context)

    classrooms = permissions.get_accessible_classrooms(request.user)
    context = {"classrooms": classrooms}
    return render(request, "dashboard/leader_dashboard.html", context)