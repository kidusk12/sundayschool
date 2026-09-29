from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from .. import exports, permissions, services
from ..audit import log_action
from ..forms import RosterColumnForm, RosterTableForm
from ..models import ActivityLog, RosterColumn, RosterRow


@permissions.classroom_access_required(url_kwarg="classroom_id")
def roster_list(request, classroom_id):
    rosters = request.classroom.rosters.order_by("-created_at")
    return render(request, "roster/list.html", {"classroom": request.classroom, "rosters": rosters})


@permissions.classroom_access_required(url_kwarg="classroom_id")
def roster_create(request, classroom_id):
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
    roster = request.roster
    form = RosterColumnForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        column = form.save(commit=False)
        column.roster = roster
        column.order = roster.columns.count()
        column.save()
        log_action(actor=request.user, action=ActivityLog.Action.CREATE, obj=column, classroom=roster.classroom)
    elif request.method == "POST":
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

    if request.htmx:
        table_html = render_to_string(
            request=request, template_name="partials/_roster_table.html", context=_roster_context(roster)
        )
        flash_html = render_to_string(request=request, template_name="partials/_flash.html", context={})
        return HttpResponse(table_html + f'<div id="flash-container" hx-swap-oob="true">{flash_html}</div>')
    return redirect("school:roster_detail", roster_id=roster.pk)


@permissions.roster_access_required(url_kwarg="roster_id")
def column_delete(request, roster_id, column_id):
    roster = request.roster
    column = get_object_or_404(RosterColumn, pk=column_id, roster=roster)
    log_action(actor=request.user, action=ActivityLog.Action.DELETE, obj=column, classroom=roster.classroom)
    column.delete()

    if request.htmx:
        return render(request, "partials/_roster_table.html", _roster_context(roster))
    return redirect("school:roster_detail", roster_id=roster.pk)


def _parse_decimal(raw):
    raw = (raw or "").strip()
    if not raw:
        return None, True
    try:
        return Decimal(raw), True
    except InvalidOperation:
        return None, False


@permissions.roster_access_required(url_kwarg="roster_id")
def update_cell(request, roster_id):
    roster = request.roster
    row = get_object_or_404(RosterRow, pk=request.POST.get("row_id"), roster=roster)
    column = get_object_or_404(RosterColumn, pk=request.POST.get("column_id"), roster=roster)
    value, ok = _parse_decimal(request.POST.get("score", ""))

    if ok:
        services.set_roster_score(row=row, column=column, score=value, user=request.user)
    else:
        messages.error(request, "ትክክለኛ ቁጥር ያስገቡ።")

    if request.htmx:
        n = RosterRow.objects.filter(
            roster=roster, student__name_key__lt=row.student.name_key
        ).count() + 1
        by_column = {s.column_id: s.score for s in row.scores.all()}
        row_html = render_to_string(request=request, template_name="partials/_roster_row.html", context={
            "row": {
                "n": n, "row": row, "student": row.student,
                "average": row.average, "rank": row.rank, "scores": by_column,
            },
            "columns": list(roster.columns.all()),
        })
        flash_html = render_to_string(request=request, template_name="partials/_flash.html", context={})
        return HttpResponse(
            row_html + f'<div id="flash-container" hx-swap-oob="true">{flash_html}</div>'
        )
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