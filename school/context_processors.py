from . import permissions


def role_flags(request):
    """Makes perms_is_head available in every template without each view
    having to pass it explicitly — base.html's nav depends on it."""
    if not request.user.is_authenticated:
        return {}
    return {"perms_is_head": permissions.is_head(request.user)}