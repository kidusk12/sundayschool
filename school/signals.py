from django.conf import settings
from django.contrib.auth.models import Group
from django.db import connections
from django.db.models.signals import post_delete, post_migrate, post_save
from django.dispatch import receiver

from .models import Profile, StudentFile

PROTECT_SQL = """
CREATE OR REPLACE FUNCTION school_activitylog_immutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'school_activitylog is append-only';
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS school_activitylog_no_change ON school_activitylog;
CREATE TRIGGER school_activitylog_no_change
    BEFORE UPDATE OR DELETE ON school_activitylog
    FOR EACH ROW EXECUTE FUNCTION school_activitylog_immutable();
"""


@receiver(post_migrate)
def after_migrate(sender, **kwargs):
    if getattr(sender, "name", None) != "school":
        return
    for name in ("Head", "ClassLeader"):
        Group.objects.using(kwargs.get("using", "default")).get_or_create(name=name)
    connection = connections[kwargs.get("using", "default")]
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(PROTECT_SQL)  # database-level guarantee that the log can't be edited


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile_exists(sender, instance, created, **kwargs):
    """Every user needs a Profile row for the forced-password-change check (SRS §4.9) to
    work at all. This covers accounts created OUTSIDE the app's own account-creation view —
    `createsuperuser`, the `seed` command, or the Django admin — so the middleware never
    hits a missing Profile and crashes instead of enforcing the rule."""
    if created:
        Profile.objects.get_or_create(user=instance)


@receiver(post_delete, sender=StudentFile)
def remove_file_from_disk(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)