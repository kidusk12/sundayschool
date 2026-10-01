from datetime import date

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from .. import ethiopic, exports, permissions, services
from ..audit import log_action
from ..models import ActivityLog, AttendanceEntry, AttendanceRow, AttendanceSheet, Student


@permissions.classroom_access_required(url_kwarg="classroom_id")
def sheet_list(request, classroom_id):
    classroom = request.classroom
    sheet, _ = AttendanceSheet.objects.get_or_create(classroom=classroom, is_template=True)
    real_sheets = AttendanceSheet.objects.filter(
        classroom=classroom, is_template=False
    ).order_by("-ethiopian_year", "-ethiopian_month")

    return render(request, "attendance/sheet_list.html", {
        "classroom": classroom,
        "template_sheet": sheet,
        "sheets": real_sheets,
        "months": list(enumerate(ethiopic.MONTHS, start=1)),
        "current_year": ethiopic.current_year(),
    })


@permissions.classroom_access_required(url_kwarg="classroom_id")
def sheet_create(request, classroom_id):
    classroom = request.classroom
    try:
        year = int(request.POST["ethiopian_year"])
        month = int(request.POST["ethiopian_month"])
        if not (1 <= month <= 13):
            raise ValueError
    except (KeyError, ValueError):
        messages.error(request, "ትክክለኛ ዓመት እና ወር ይምረጡ።")
        return redirect("school:attendance_sheet_list", classroom_id=classroom.pk)

    sheet, created = AttendanceSheet.objects.get_or_create(
        classroom=classroom, ethiopian_year=year, ethiopian_month=month, is_template=False,
    )
    if not created:
        messages.info(request, "ይህ ወር ቀደም ብሎ ተፈጥሯል፤ ወደ እሱ ተወስደዋል።")
    return redirect("school:attendance_sheet_detail", sheet_id=sheet.pk)


def _sheet_context(sheet):
    sundays = [] if sheet.is_template else ethiopic.sundays_in_month(
        sheet.ethiopian_year, sheet.ethiopian_month
    )
    rows_qs = (
        AttendanceRow.objects.filter(sheet=sheet)
        .select_related("student")
        .prefetch_related("entries")
        .order_by("student__name_key")
    )
    rows = []
    for i, row in enumerate(rows_qs, start=1):
        by_date = {e.sunday_date: e.status for e in row.entries.all()}
        totals = services.attendance_totals(row)
        rows.append({
            "n": i,
            "row": row,
            "student": row.student,
            "cells": [{"date": d, "status": by_date.get(d, "")} for d in sundays],
            "present": totals["present"],
            "absent": totals["absent"],
            "permission": totals["permission"],
        })

    enrolled_ids = {r["student"].pk for r in rows}
    available_students = Student.objects.filter(classroom=sheet.classroom).exclude(
        pk__in=enrolled_ids
    ).order_by("name_key")

    return {
        "sheet": sheet,
        "sundays": sundays,
        "rows": rows,
        "available_students": available_students,
        "title": exports.sheet_title(sheet),
    }


@permissions.attendance_sheet_access_required(url_kwarg="sheet_id")
def sheet_detail(request, sheet_id):
    context = _sheet_context(request.sheet)
    return render(request, "attendance/sheet_detail.html", context)


@permissions.attendance_sheet_access_required(url_kwarg="sheet_id")
def add_student(request, sheet_id):
    sheet = request.sheet
    student_id = request.POST.get("student_id")
    student = get_object_or_404(Student, pk=student_id, classroom=sheet.classroom)

    try:
        services.add_student_to_sheet(sheet=sheet, student=student, user=request.user)
    except (services.CrossClassError, ValueError) as exc:
        messages.error(request, str(exc))

    if request.htmx:
        table_html = render_to_string(
            request=request, template_name="partials/_attendance_table.html", context=_sheet_context(sheet)
        )
        flash_html = render_to_string(request=request, template_name="partials/_flash.html", context={})
        return HttpResponse(table_html + f'<div id="flash-container" hx-swap-oob="true">{flash_html}</div>')
    return redirect("school:attendance_sheet_detail", sheet_id=sheet.pk)


@permissions.attendance_sheet_access_required(url_kwarg="sheet_id")
def mark_cell(request, sheet_id):
    sheet = request.sheet
    row = get_object_or_404(AttendanceRow, pk=request.POST.get("row_id"), sheet=sheet)
    sunday_date = date.fromisoformat(request.POST["sunday"])
    status = request.POST.get("status", "")

    if status:
        services.mark_attendance(row=row, sunday_date=sunday_date, status=status, user=request.user)
    else:
        services.clear_attendance_entry(row=row, sunday_date=sunday_date, user=request.user)

    if request.htmx:
        n = AttendanceRow.objects.filter(
            sheet=sheet, student__name_key__lt=row.student.name_key
        ).count() + 1
        by_date = {e.sunday_date: e.status for e in row.entries.all()}
        totals = services.attendance_totals(row)
        return render(request, "partials/_attendance_row.html", {
            "row": {
                "n": n, "row": row, "student": row.student,
                "cells": [{"date": d, "status": by_date.get(d, "")} for d in ethiopic.sundays_in_month(
                    sheet.ethiopian_year, sheet.ethiopian_month
                )],
                **totals,
            },
        })
    return redirect("school:attendance_sheet_detail", sheet_id=sheet.pk)


@permissions.attendance_sheet_access_required(url_kwarg="sheet_id")
def sheet_export(request, sheet_id):
    sheet = request.sheet
    context = _sheet_context(sheet)
    fmt = request.GET.get("format", "pdf")

    log_action(actor=request.user, action=ActivityLog.Action.EXPORT, obj=sheet, classroom=sheet.classroom)

    if fmt == "xlsx":
        workbook = exports.attendance_workbook(sheet, context["sundays"], context["rows"])
        return exports.xlsx_response(workbook, f"attendance-{sheet.pk}.xlsx")
    return exports.pdf_response("pdf/attendance.html", context, f"attendance-{sheet.pk}.pdf")