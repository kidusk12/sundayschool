from django.shortcuts import redirect
from django.urls import reverse

from .models import Profile

# Reachable even while a password change is pending — matches api/permissions.py's
# earlier PASSWORD_CHANGE_EXEMPT_PATHS list conceptually, but as URL *names* here
# since this is resolved via reverse(), not raw paths.
EXEMPT_URL_NAMES = {
    "school:login",
    "school:logout",
    "school:force_password_change",
}


class ForcePasswordChangeMiddleware:
    """SRS §4.9: every page redirects to the change-password screen while
    must_change_password is set, except login/logout/the change-password
    view itself. One piece of middleware, checked once per request — not a
    rule re-declared on every view (this is the whole reason we moved away
    from the DRF version's get_permissions()-override pattern, which kept
    silently dropping this exact check).

    /admin/ is also exempt: a superuser is infrastructure, not one of the
    SRS's two modeled roles (Head/Class Leader), and an emergency escape
    hatch shouldn't be blockable by the same app-level rule it exists to
    bypass."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_paths = {reverse(name) for name in EXEMPT_URL_NAMES}

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and request.path not in self.exempt_paths
            and not request.path.startswith("/admin/")
        ):
            profile, _ = Profile.objects.get_or_create(user=request.user)
            if profile.must_change_password:
                return redirect("school:force_password_change")
        return self.get_response(request)