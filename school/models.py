from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q, F, CheckConstraint, UniqueConstraint
from django.utils import timezone
from .validators import validate_ethiopian_phone
from .ethiopic import normalize_name


# ---------------------------------------------------------------------------
# 3.1 Identity and access
# ---------------------------------------------------------------------------

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    must_change_password = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username


class ClassAssignment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="class_assignments")
    classroom = models.ForeignKey("ClassRoom", on_delete=models.CASCADE, related_name="assignments")

    class Meta:
        constraints = [
            UniqueConstraint(fields=["user", "classroom"], name="unique_user_classroom"),
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.classroom.name}"


# ---------------------------------------------------------------------------
# 3.2 Classes
# ---------------------------------------------------------------------------

class ClassRoom(models.Model):
    name = models.CharField(max_length=100, unique=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    min_age = models.PositiveSmallIntegerField(null=True, blank=True)
    max_age = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            CheckConstraint(
                check=Q(min_age__isnull=True) | Q(max_age__isnull=True) | Q(min_age__lte=F("max_age")),
                name="classroom_min_age_lte_max_age",
            ),
        ]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# 3.3 Students
# ---------------------------------------------------------------------------

class Student(models.Model):
    first_name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100)
    grandfather_name = models.CharField(max_length=100)
    name_key = models.CharField(max_length=300,  editable=False)

    age = models.PositiveSmallIntegerField(null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)

    phone = models.CharField(max_length=20, blank=True, validators=[validate_ethiopian_phone])
    parent_phone_1 = models.CharField(max_length=20, blank=True, validators=[validate_ethiopian_phone])
    parent_phone_2 = models.CharField(max_length=20, blank=True, validators=[validate_ethiopian_phone])

    background_notes = models.TextField(blank=True)

    classroom = models.ForeignKey(ClassRoom, on_delete=models.PROTECT, related_name="students")

    registered_at = models.DateField(default=timezone.localdate)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="registered_students"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["name_key"])]

    def save(self, *args, **kwargs):
        self.name_key = normalize_name(self.first_name, self.father_name, self.grandfather_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.father_name} {self.grandfather_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.father_name} {self.grandfather_name}"

# ---------------------------------------------------------------------------
# 3.4 Attendance
# ---------------------------------------------------------------------------

class AttendanceSheet(models.Model):
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name="attendance_sheets")
    ethiopian_year = models.PositiveSmallIntegerField(null=True, blank=True)
    ethiopian_month = models.PositiveSmallIntegerField(null=True, blank=True)
    is_template = models.BooleanField(default=False)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["classroom", "ethiopian_year", "ethiopian_month"],
                condition=Q(is_template=False),
                name="unique_class_month_sheet",
            ),
            UniqueConstraint(
                fields=["classroom"],
                condition=Q(is_template=True),
                name="unique_class_template_sheet",
            ),
        ]

    def __str__(self):
        if self.is_template:
            return f"{self.classroom.name} (template)"
        return f"{self.classroom.name} {self.ethiopian_year}/{self.ethiopian_month}"


class AttendanceRow(models.Model):
    sheet = models.ForeignKey(AttendanceSheet, on_delete=models.CASCADE, related_name="rows")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendance_rows")
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["sheet", "student"], name="unique_student_per_sheet"),
        ]


class AttendanceEntry(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        PERMISSION = "permission", "Permission"

    row = models.ForeignKey(AttendanceRow, on_delete=models.CASCADE, related_name="entries")
    sunday_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices)
    marked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["row", "sunday_date"], name="unique_entry_per_row_per_sunday"),
        ]


# ---------------------------------------------------------------------------
# 3.5 Marks
# ---------------------------------------------------------------------------

class MarkList(models.Model):
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name="mark_lists")
    name = models.CharField(max_length=200)
    teacher = models.CharField(max_length=200, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    year = models.CharField(max_length=20, blank=True)
    semester = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class MarkColumn(models.Model):
    mark_list = models.ForeignKey(MarkList, on_delete=models.CASCADE, related_name="columns")
    name = models.CharField(max_length=100)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class Mark(models.Model):
    mark_list = models.ForeignKey(MarkList, on_delete=models.CASCADE, related_name="marks")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="marks")
    total = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["mark_list", "student"], name="unique_student_per_marklist"),
        ]


class MarkColumnScore(models.Model):
    mark = models.ForeignKey(Mark, on_delete=models.CASCADE, related_name="column_scores")
    column = models.ForeignKey(MarkColumn, on_delete=models.CASCADE, related_name="scores")
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["mark", "column"], name="unique_score_per_mark_per_column"),
        ]


# ---------------------------------------------------------------------------
# 3.6 Roster
# ---------------------------------------------------------------------------

class RosterTable(models.Model):
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name="rosters")
    year = models.CharField(max_length=20, blank=True)
    semester = models.CharField(max_length=20, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    calculated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    calculated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.classroom.name} {self.year}/{self.semester}"


class RosterColumn(models.Model):
    roster = models.ForeignKey(RosterTable, on_delete=models.CASCADE, related_name="columns")
    subject_name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class RosterRow(models.Model):
    roster = models.ForeignKey(RosterTable, on_delete=models.CASCADE, related_name="rows")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="roster_rows")
    average = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    rank = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["roster", "student"], name="unique_student_per_roster"),
        ]


class RosterScore(models.Model):
    row = models.ForeignKey(RosterRow, on_delete=models.CASCADE, related_name="scores")
    column = models.ForeignKey(RosterColumn, on_delete=models.CASCADE, related_name="scores")
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["row", "column"], name="unique_score_per_row_per_column"),
        ]


# ---------------------------------------------------------------------------
# 3.7 Files
# ---------------------------------------------------------------------------

class StudentFile(models.Model):
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, null=True, blank=True, related_name="files"
    )
    classroom = models.ForeignKey(
        ClassRoom, on_delete=models.CASCADE, null=True, blank=True, related_name="files"
    )
    file = models.FileField(upload_to="student_files/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            CheckConstraint(
                check=Q(student__isnull=False) | Q(classroom__isnull=False),
                name="studentfile_has_student_or_classroom",
            ),
        ]


# ---------------------------------------------------------------------------
# 3.8 Removal requests and activity log
# ---------------------------------------------------------------------------

class RemovalRequest(models.Model):
    target_label = models.CharField(max_length=255, blank=True)
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DELETED = "deleted", "Deleted"
        DISMISSED = "dismissed", "Dismissed"

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name="removal_requests")
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="filed_removal_requests"
    )
    requested_at = models.DateTimeField(auto_now_add=True)

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["content_type", "object_id"])]


class ActivityLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        REMOVAL_REQUESTED = "removal_requested", "Removal requested"
        REQUEST_DISMISSED = "request_dismissed", "Request dismissed"
        EXPORT = "export", "Export"
        LOGIN = "login", "Login"
        MOVE = "move", "Move"
        CALCULATE = "calculate", "Calculate"

    timestamp = models.DateTimeField(auto_now_add=True)

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    actor_name = models.CharField(max_length=150)

    action = models.CharField(max_length=20, choices=Action.choices)
    object_type = models.CharField(max_length=100)
    object_label = models.CharField(max_length=255)

    classroom = models.ForeignKey(ClassRoom, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["actor"]),
            models.Index(fields=["action"]),
            models.Index(fields=["object_type"]),
            models.Index(fields=["classroom"]),
            models.Index(fields=["timestamp"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("ActivityLog is append-only and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("ActivityLog is append-only and cannot be deleted.")