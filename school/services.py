from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone


from . import permissions
from . import registry
from .audit import log_action
from .ethiopic import normalize_name
from .models import (
    ActivityLog,
    AttendanceEntry,
    AttendanceRow,
    AttendanceSheet,
    ClassAssignment,
    Mark,
    MarkList,
    MarkColumn,
    RemovalRequest,
    RosterColumn,
    RosterRow,
    RosterScore,
    RosterTable,
    Student,
    MarkColumnScore, 
)


# ---------------------------------------------------------------------------
# 4.1 / 4.2 Registration and existing-student match check
# ---------------------------------------------------------------------------

def find_existing_student(first_name, father_name, grandfather_name):
    key = normalize_name(first_name, father_name, grandfather_name)
    return Student.objects.filter(name_key=key).select_related("classroom").first()


def can_view_full_match_detail(user, matched_student):
    if permissions.is_head(user):
        return True
    return ClassAssignment.objects.filter(user=user, classroom=matched_student.classroom).exists()

@transaction.atomic
def register_student(*, form, user):
    student = form.save(commit=False)
    student.registered_by = user
    student.save()

    log_action(
        actor=user,
        action=ActivityLog.Action.CREATE,
        obj=student,
        classroom=student.classroom,
        new_values={
            "first_name": student.first_name,
            "father_name": student.father_name,
            "grandfather_name": student.grandfather_name,
            "classroom": student.classroom.name,
        },
    )
    return student


# ---------------------------------------------------------------------------
# 4.3 Manual enrollment onto attendance sheets / mark lists
# ---------------------------------------------------------------------------

class CrossClassError(Exception):
    """Raised when a student and the sheet/list they're being added to
    belong to different classes — this can never be a valid Add-student."""


@transaction.atomic
def add_student_to_sheet(*, sheet, student, user):
    if sheet.is_template:
        raise ValueError("The template attendance sheet is never populated.")
    if student.classroom_id != sheet.classroom_id:
        raise CrossClassError("This student is not in the sheet's class.")

    row, created = AttendanceRow.objects.get_or_create(
        sheet=sheet, student=student, defaults={"added_by": user}
    )
    if created:
        log_action(
            actor=user,
            action=ActivityLog.Action.CREATE,
            obj=row,
            classroom=sheet.classroom,
            new_values={"student": str(student), "sheet": str(sheet)},
        )
    return row, created


@transaction.atomic
def add_student_to_marklist(*, mark_list, student, user):
    if student.classroom_id != mark_list.classroom_id:
        raise CrossClassError("This student is not in the mark list's class.")

    mark, created = Mark.objects.get_or_create(mark_list=mark_list, student=student)
    if created:
        log_action(
            actor=user,
            action=ActivityLog.Action.CREATE,
            obj=mark,
            classroom=mark_list.classroom,
            new_values={"student": str(student), "mark_list": mark_list.name},
        )
    return mark, created

@transaction.atomic
def set_mark_total(*, mark, total, user):
    old_total = mark.total
    mark.total = total
    mark.save(update_fields=["total"])
    log_action(
        actor=user, action=ActivityLog.Action.UPDATE, obj=mark,
        classroom=mark.mark_list.classroom,
        old_values={"total": str(old_total) if old_total is not None else None},
        new_values={"total": str(total) if total is not None else None},
    )
    return mark


def set_mark_column_score(*, mark, column, score, user):
    """Not separately logged — these are the owner's own working-notes columns
    (SRS §4.4), the Total (logged above) is the number that actually matters."""
    obj, _ = MarkColumnScore.objects.get_or_create(mark=mark, column=column, defaults={"score": score})
    obj.score = score
    obj.save(update_fields=["score"])
    return obj


def set_roster_score(*, row, column, score, user):
    """Not logged per-cell either — 'calculate_roster' (already logs CALCULATE)
    is the meaningful checkpoint for a roster, not each individual typed score."""
    obj, _ = RosterScore.objects.get_or_create(row=row, column=column, defaults={"score": score})
    obj.score = score
    obj.save(update_fields=["score"])
    return obj

# ---------------------------------------------------------------------------
# 4.5 Attendance
# ---------------------------------------------------------------------------

@transaction.atomic
def mark_attendance(*, row, sunday_date, status, user):
    entry, created = AttendanceEntry.objects.get_or_create(
        row=row, sunday_date=sunday_date, defaults={"status": status, "marked_by": user}
    )
    old_status = None if created else entry.status
    if not created:
        entry.status = status
        entry.marked_by = user
        entry.save()

    log_action(
        actor=user,
        action=ActivityLog.Action.CREATE if created else ActivityLog.Action.UPDATE,
        obj=entry,
        classroom=row.sheet.classroom,
        old_values=None if created else {"status": old_status},
        new_values={"status": status},
    )
    return entry


def attendance_totals(row):
    counts = {"present": 0, "absent": 0, "permission": 0}
    for entry in row.entries.all():
        counts[entry.status] = counts.get(entry.status, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# 4.4 Mark lists — duplicate
# ---------------------------------------------------------------------------

@transaction.atomic
def duplicate_marklist(*, mark_list, user):
    new_list = MarkList.objects.create(
        classroom=mark_list.classroom,
        name=mark_list.name,
        teacher=mark_list.teacher,
        subject=mark_list.subject,
        year=mark_list.year,
        semester=mark_list.semester,
    )

    column_map = {}
    for column in mark_list.columns.all():
        new_column = MarkColumn.objects.create(
            mark_list=new_list, name=column.name, max_score=column.max_score, order=column.order
        )
        column_map[column.id] = new_column

    for mark in mark_list.marks.all():
        new_mark = Mark.objects.create(mark_list=new_list, student=mark.student, total=None)
        for score in mark.column_scores.all():
            MarkColumnScore.objects.create(
                mark=new_mark, column=column_map[score.column_id], score=None
            )

    log_action(
        actor=user,
        action=ActivityLog.Action.CREATE,
        obj=new_list,
        classroom=new_list.classroom,
        new_values={"duplicated_from": mark_list.name},
    )
    return new_list


# ---------------------------------------------------------------------------
# 4.6 Roster — create, duplicate, calculate
# ---------------------------------------------------------------------------

@transaction.atomic
def create_roster(*, classroom, year, semester, user):
    roster = RosterTable.objects.create(
        classroom=classroom, year=year, semester=semester, created_by=user
    )
    for student in classroom.students.all():
        RosterRow.objects.create(roster=roster, student=student)

    log_action(
        actor=user,
        action=ActivityLog.Action.CREATE,
        obj=roster,
        classroom=classroom,
        new_values={"year": year, "semester": semester},
    )
    return roster


@transaction.atomic
def duplicate_roster(*, roster, user):
    new_roster = RosterTable.objects.create(
        classroom=roster.classroom, year="", semester="", created_by=user
    )
    for student in roster.classroom.students.all():
        RosterRow.objects.create(roster=new_roster, student=student)

    log_action(
        actor=user,
        action=ActivityLog.Action.CREATE,
        obj=new_roster,
        classroom=new_roster.classroom,
        new_values={"duplicated_from": str(roster)},
    )
    return new_roster


def _round2(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@transaction.atomic
def calculate_roster(*, roster, user):
    rows = list(roster.rows.prefetch_related("scores"))

    averages = []
    for row in rows:
        scores = [s.score for s in row.scores.all() if s.score is not None]
        avg = _round2(sum(scores) / len(scores)) if scores else None
        averages.append((row, avg))

    ranked = sorted(
        [(row, avg) for row, avg in averages if avg is not None],
        key=lambda pair: pair[1],
        reverse=True,
    )

    rank = 0
    previous_avg = None
    seen = 0
    for row, avg in ranked:
        seen += 1
        if avg != previous_avg:
            rank = seen
            previous_avg = avg
        row.average = avg
        row.rank = rank
        row.save()

    for row, avg in averages:
        if avg is None:
            row.average = None
            row.rank = None
            row.save()

    roster.calculated_by = user
    roster.calculated_at = timezone.now()
    roster.save()

    log_action(
        actor=user,
        action=ActivityLog.Action.CALCULATE,
        obj=roster,
        classroom=roster.classroom,
        new_values={"row_count": len(rows)},
    )
    return roster


# ---------------------------------------------------------------------------
# 4.7 Removal requests
# ---------------------------------------------------------------------------

@transaction.atomic
def file_removal_request(*, target, reason, user):
    if not registry.is_removable(target):
        raise registry.NotRemovableError(
            f"{type(target).__name__} cannot be requested for removal."
        )
    if isinstance(target, AttendanceSheet) and target.is_template:
        raise registry.NotRemovableError("The template attendance sheet cannot be removed.")
    classroom = registry.get_classroom_for(target)

    request = RemovalRequest.objects.create(
        content_object=target,
        classroom=classroom,
        target_label=f"{registry.get_label_for(target)}: {target}",
        reason=reason,
        requested_by=user,
    )
    log_action(
        actor=user,
        action=ActivityLog.Action.REMOVAL_REQUESTED,
        obj=request,
        classroom=classroom,
        new_values={"target": str(target), "reason": reason},
    )
    return request

@transaction.atomic
def resolve_removal_request(*, request, approve, user):
    target = request.content_object

    if approve:
        request.status = RemovalRequest.Status.DELETED
        request.resolved_by = user
        request.resolved_at = timezone.now()
        request.save()
        if target is not None:
            delete_object(obj=target, user=user)
    else:
        request.status = RemovalRequest.Status.DISMISSED
        request.resolved_by = user
        request.resolved_at = timezone.now()
        request.save()
        log_action(
            actor=user,
            action=ActivityLog.Action.REQUEST_DISMISSED,
            obj=request,
            classroom=request.classroom,
        )
    return request

# ---------------------------------------------------------------------------
# Central deletion — used by Head direct-delete and by removal resolution
# ---------------------------------------------------------------------------

class ProtectedObjectError(Exception):
    pass


@transaction.atomic
def delete_object(*, obj, user):
    from .models import AttendanceSheet

    if isinstance(obj, AttendanceSheet) and obj.is_template:
        raise ProtectedObjectError("The template attendance sheet cannot be deleted.")

    classroom = registry.get_classroom_for(obj) if registry.is_removable(obj) else None
    label = str(obj)

    log_action(
        actor=user,
        action=ActivityLog.Action.DELETE,
        obj=obj,
        classroom=classroom,
        old_values={"label": label},
    )
    obj.delete()

@transaction.atomic
def clear_attendance_entry(*, row, sunday_date, user):
    """Un-marks a previously-marked cell back to blank (no AttendanceEntry row at
    all) — the model has no blank status choice, so 'clearing' means deleting."""
    deleted, _ = AttendanceEntry.objects.filter(row=row, sunday_date=sunday_date).delete()
    if deleted:
        log_action(
            actor=user, action=ActivityLog.Action.DELETE, obj=row,
            classroom=row.sheet.classroom,
            old_values={"sunday_date": str(sunday_date)},
            note="የመገኘት ምልክት ተነስቷል (attendance mark cleared)",
        )

