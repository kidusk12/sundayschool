from .models import ActivityLog


def log_action(*, actor, action, obj, classroom=None, old_values=None, new_values=None, note=""):
    return ActivityLog.objects.create(
        actor=actor,
        actor_name=actor.username if actor else "",
        action=action,
        object_type=obj.__class__.__name__,
        object_label=str(obj),
        classroom=classroom,
        old_values=old_values,
        new_values=new_values,
        note=note,
    )