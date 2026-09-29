from functools import wraps

from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import AttendanceSheet
from .models import ClassAssignment, ClassRoom, Student
from .models import AttendanceSheet, MarkList, RosterTable  # extend existing models import


HEAD_GROUP_NAME = "Head"

def attendance_sheet_access_required(url_kwarg="sheet_id"):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            sheet = get_object_or_404(AttendanceSheet, pk=kwargs.get(url_kwarg))
            if not can_access_classroom(request.user, sheet.classroom):
                raise PermissionDenied
            request.sheet = sheet
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def is_head(user):
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name=HEAD_GROUP_NAME).exists()


def assigned_classroom_ids(user):
    return set(ClassAssignment.objects.filter(user=user).values_list("classroom_id", flat=True))


def get_accessible_classrooms(user):
    if is_head(user):
        return ClassRoom.objects.all()
    return ClassRoom.objects.filter(assignments__user=user).distinct()


def can_access_classroom(user, classroom):
    if is_head(user):
        return True
    return classroom.id in assigned_classroom_ids(user)


def can_access_student(user, student):
    return can_access_classroom(user, student.classroom)


def can_view_full_student_detail(user, student):
    return can_access_classroom(user, student.classroom)


def can_delete_directly(user):
    return is_head(user)


def can_manage_accounts(user):
    return is_head(user)


def can_manage_classes(user):
    return is_head(user)


def can_view_activity_log(user):
    return is_head(user)


def can_resolve_removal_requests(user):
    return is_head(user)


# ---------------------------------------------------------------------------
# Decorators for views
# ---------------------------------------------------------------------------

def head_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_head(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


def classroom_access_required(url_kwarg="classroom_id"):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            classroom = get_object_or_404(ClassRoom, pk=kwargs.get(url_kwarg))
            if not can_access_classroom(request.user, classroom):
                raise PermissionDenied
            request.classroom = classroom
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def student_access_required(url_kwarg="student_id"):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            student = get_object_or_404(Student, pk=kwargs.get(url_kwarg))
            if not can_access_student(request.user, student):
                raise PermissionDenied
            request.student = student
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def mark_list_access_required(url_kwarg="mark_list_id"):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            mark_list = get_object_or_404(MarkList, pk=kwargs.get(url_kwarg))
            if not can_access_classroom(request.user, mark_list.classroom):
                raise PermissionDenied
            request.mark_list = mark_list
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def roster_access_required(url_kwarg="roster_id"):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            roster = get_object_or_404(RosterTable, pk=kwargs.get(url_kwarg))
            if not can_access_classroom(request.user, roster.classroom):
                raise PermissionDenied
            request.roster = roster
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator