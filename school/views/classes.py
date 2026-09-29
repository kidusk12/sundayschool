from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .. import permissions
from ..audit import log_action
from ..forms import ClassRoomForm
from ..models import ActivityLog, ClassRoom


@permissions.head_required
def class_list(request):
    classrooms = ClassRoom.objects.all()  # both active and inactive — Head needs to see both
    return render(request, "classes/class_list.html", {"classrooms": classrooms})


@permissions.head_required
def class_create(request):
    form = ClassRoomForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        classroom = form.save()
        log_action(actor=request.user, action=ActivityLog.Action.CREATE, obj=classroom,
                   classroom=classroom, new_values={"name": classroom.name})
        messages.success(request, "ክፍል ተፈጥሯል።")
        return redirect("school:class_list")

    return render(request, "classes/class_form.html", {"form": form, "is_new": True})


@permissions.head_required
def class_edit(request, classroom_id):
    classroom = get_object_or_404(ClassRoom, pk=classroom_id)
    old_values = {
        "name": classroom.name, "is_active": classroom.is_active,
        "min_age": classroom.min_age, "max_age": classroom.max_age,
    }
    form = ClassRoomForm(request.POST or None, instance=classroom)
    if request.method == "POST" and form.is_valid():
        classroom = form.save()
        log_action(actor=request.user, action=ActivityLog.Action.UPDATE, obj=classroom,
                   classroom=classroom, old_values=old_values,
                   new_values={
                       "name": classroom.name, "is_active": classroom.is_active,
                       "min_age": classroom.min_age, "max_age": classroom.max_age,
                   })
        messages.success(request, "ክፍል ተስተካክሏል።")
        return redirect("school:class_list")

    return render(request, "classes/class_form.html", {"form": form, "is_new": False, "classroom": classroom})


@permissions.classroom_access_required(url_kwarg="classroom_id")
@login_required
def class_detail(request, classroom_id):
    """The hub page for one class — sidebar/tabs into attendance, mark lists,
    roster, students, and files, all scoped to this classroom (SRS §3.2)."""
    classroom = request.classroom  # set by classroom_access_required
    return render(request, "classes/class_detail.html", {"classroom": classroom})