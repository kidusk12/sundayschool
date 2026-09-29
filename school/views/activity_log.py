from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.shortcuts import render

from .. import permissions
from ..models import ActivityLog, ClassRoom

User = get_user_model()


@permissions.head_required
def activity_log_list(request):
    logs = ActivityLog.objects.select_related("actor", "classroom").all()

    actor_id = request.GET.get("actor")
    if actor_id:
        logs = logs.filter(actor_id=actor_id)

    action = request.GET.get("action")
    if action:
        logs = logs.filter(action=action)

    object_type = request.GET.get("object_type")
    if object_type:
        logs = logs.filter(object_type=object_type)

    classroom_id = request.GET.get("classroom")
    if classroom_id:
        logs = logs.filter(classroom_id=classroom_id)

    date_from = request.GET.get("from")
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)

    date_to = request.GET.get("to")
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)

    paginator = Paginator(logs, 50)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "activity_log/list.html", {
        "page": page,
        "actors": User.objects.filter(activitylog__isnull=False).distinct().order_by("username"),
        "actions": ActivityLog.Action.choices,
        "object_types": ActivityLog.objects.values_list("object_type", flat=True).distinct().order_by("object_type"),
        "classrooms": ClassRoom.objects.all(),
        "filters": {
            "actor": actor_id or "",
            "action": action or "",
            "object_type": object_type or "",
            "classroom": classroom_id or "",
            "from": date_from or "",
            "to": date_to or "",
        },
    })