from django.contrib.contenttypes.models import ContentType

from .models import (
    AttendanceRow,
    AttendanceSheet,
    Mark,
    MarkList,
    Student,
    StudentFile,
)

# ---------------------------------------------------------------------------
# Registry of object types that a class leader may target with a removal
# request (SRS §4.7). Anything not listed here cannot be filed against,
# regardless of role.
# ---------------------------------------------------------------------------

REMOVABLE_REGISTRY = {
    Student: {
        "label": "Student",
        "get_classroom": lambda obj: obj.classroom,
    },
    AttendanceSheet: {
        "label": "Attendance sheet",
        "get_classroom": lambda obj: obj.classroom,
    },
    AttendanceRow: {
        "label": "Attendance row",
        "get_classroom": lambda obj: obj.sheet.classroom,
    },
    MarkList: {
        "label": "Mark list",
        "get_classroom": lambda obj: obj.classroom,
    },
    Mark: {
        "label": "Mark list row",
        "get_classroom": lambda obj: obj.mark_list.classroom,
    },
    StudentFile: {
        "label": "File",
        "get_classroom": lambda obj: obj.classroom or obj.student.classroom,
    },
}


class NotRemovableError(Exception):
    pass


def is_removable(obj):
    return type(obj) in REMOVABLE_REGISTRY


def get_removable_config(obj):
    config = REMOVABLE_REGISTRY.get(type(obj))
    if config is None:
        raise NotRemovableError(f"{type(obj).__name__} cannot be targeted by a removal request.")
    return config


def get_label_for(obj):
    return get_removable_config(obj)["label"]


def get_classroom_for(obj):
    return get_removable_config(obj)["get_classroom"](obj)


def removable_content_type_ids():
    """Used to constrain RemovalRequest's GenericForeignKey choices."""
    return [
        ContentType.objects.get_for_model(model).id
        for model in REMOVABLE_REGISTRY
    ]