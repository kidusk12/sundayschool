from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .. import exports, permissions, services
from ..audit import log_action
from ..forms import RosterColumnForm, RosterTableForm
from ..models import ActivityLog, RosterColumn, RosterRow


@permissions.classroom_access_required(url_kwarg="classroom_id")
def roster_list(request, classroom_id):
    """A class's saved rosters, one per year/semester — click one to open it,
    same pattern as attendance's one-sheet-per-month (SRS §4.6)."""
    rosters = request.classroom.rosters.order_by("-created_at")
    return render(request, "roster/list.html", {"classroom": request.classroom, "rosters": rosters})


@permissions.classroom_access_required(url_kwarg="classroom_id")
def roster_create(request, classroom_id):
    """Brand-new (not duplicate): pre-filled with every current student, no
    columns/scores yet — a roster is whole-class by nature (§4.6)."""
    form = RosterTableForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        roster = services.create_roster(
            classroom=request.classroom, year=form.cleaned_data["year"],
            semester=form.cleaned_data["semester"], user=request.user,
        )
        return redirect("school:roster_detail", roster_id=roster.pk)

    return render(request, "roster/form.html", {"form": form, "classroom": request.classroom, "is_new": True})


@permissions.roster_access_required(url_kwarg="roster_id")
def roster_duplicate(request, roster_id):
    """Carries over only the student list — year, semester, columns, scores,
    average/rank all start blank on the copy (§4.6)."""
    new_roster = services.duplicate_roster(roster=request.roster, user=request.user)
    messages.success(request, "ሮስተር ተባዝቷል።")
    return redirect("school:roster_detail", roster_id=new_roster.pk)


def _roster_context(roster):
    columns = list(roster.columns.all())
    rows_qs = roster.rows.select_related("student").prefetch_related("scores").order_by("student__name_key")
    rows = []
    for i, row in enumerate(rows_qs, start=1):
        by_column = {s.column_id: s.score for s in row.scores.all()}
        rows.append({
            "n": i, "row": row, "student": row.student, "average": row.average, "rank": row.rank,
            "scores": {c.pk: by_column.get(c.pk) for c in columns},
        })
    return {"roster": roster, "columns": columns, "rows": rows}


@permissions.roster_access_required(url_kwarg="roster_id")
def roster_detail(request, roster_id):
    return render(request, "roster/detail.html", _roster_context(request.roster))


@permissions.roster_access_required(url_kwarg="roster_id")
def roster_edit_header(request, roster_id):
    form = RosterTableForm(request.POST or None, instance=request.roster)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "የሮስተር መረጃ ተስተካክሏል።")
        return redirect("school:roster_detail", roster_id=request.roster.pk)
    return render(request, "roster/form.html", {
        "form": form, "classroom": request.roster.classroom, "is_new": False, "roster": request.roster,
    })


@permissions.roster_access_required(url_kwarg="roster_id")
def column_create(request, roster_id):
    """Owner-typed subject names — not linked to any real MarkList (§4.6).
    Structural, so no removal-request gate, same as mark-list columns."""
    roster = request.roster
    form = RosterColumnForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        column = form.save(commit=False)
        column.roster = roster
        column.order = roster.columns.count()
        column.save()
        log_action(actor=request.user, action=ActivityLog.Action.CREATE, obj=column, classroom=roster.classroom)

    if request.htmx:
        return render(request, "roster/_table.html", _roster_context(roster))
    return redirect("school:roster_detail", roster_id=roster.pk)


@permissions.roster_access_required(url_kwarg="roster_id")
def column_delete(request, roster_id, column_id):
    roster = request.roster
    column = get_object_or_404(RosterColumn, pk=column_id, roster=roster)
    log_action(actor=request.user, action=ActivityLog.Action.DELETE, obj=column, classroom=roster.classroom)
    column.delete()

    if request.htmx:
        return render(request, "roster/_table.html", _roster_context(roster))
    return redirect("school:roster_detail", roster_id=roster.pk)


@permissions.roster_access_required(url_kwarg="roster_id")
def update_cell(request, roster_id):
    roster = request.roster
    row = get_object_or_404(RosterRow, pk=request.POST.get("row_id"), roster=roster)
    column = get_object_or_404(RosterColumn, pk=request.POST.get("column_id"), roster=roster)
    value = request.POST.get("score", "").strip()
    services.set_roster_score(row=row, column=column, score=value or None, user=request.user)

    if request.htmx:
        return render(request, "roster/_table.html", _roster_context(roster))
    return redirect("school:roster_detail", roster_id=roster.pk)


@permissions.roster_access_required(url_kwarg="roster_id")
def calculate(request, roster_id):
    services.calculate_roster(roster=request.roster, user=request.user)
    messages.success(request, "አማካኝ እና ደረጃ ተሰልቷል።")
    return redirect("school:roster_detail", roster_id=request.roster.pk)


@permissions.roster_access_required(url_kwarg="roster_id")
def roster_export(request, roster_id):
    roster = request.roster
    context = _roster_context(roster)
    fmt = request.GET.get("format", "pdf")
    log_action(actor=request.user, action=ActivityLog.Action.EXPORT, obj=roster, classroom=roster.classroom)

    if fmt == "xlsx":
        workbook = exports.roster_workbook(roster, context["columns"], context["rows"])
        return exports.xlsx_response(workbook, f"roster-{roster.pk}.xlsx")
    return exports.pdf_response("pdf/roster.html", context, f"roster-{roster.pk}.pdf")