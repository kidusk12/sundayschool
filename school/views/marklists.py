from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.http import HttpResponse

from .. import exports, permissions, services
from ..audit import log_action
from ..forms import MarkColumnForm, MarkListForm
from ..models import ActivityLog, Mark, MarkColumn, MarkColumnScore, Student


@permissions.classroom_access_required(url_kwarg="classroom_id")
def mark_list_list(request, classroom_id):
    lists = request.classroom.mark_lists.order_by("-created_at")
    return render(request, "marklists/list.html", {"classroom": request.classroom, "lists": lists})


@permissions.classroom_access_required(url_kwarg="classroom_id")
def mark_list_create(request, classroom_id):
    form = MarkListForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        mark_list = form.save(commit=False)
        mark_list.classroom = request.classroom
        mark_list.save()
        log_action(actor=request.user, action=ActivityLog.Action.CREATE, obj=mark_list,
                   classroom=request.classroom, new_values={"name": mark_list.name})
        return redirect("school:mark_list_detail", mark_list_id=mark_list.pk)

    return render(request, "marklists/form.html", {"form": form, "classroom": request.classroom, "is_new": True})


@permissions.mark_list_access_required(url_kwarg="mark_list_id")
def mark_list_duplicate(request, mark_list_id):
    new_list = services.duplicate_marklist(mark_list=request.mark_list, user=request.user)
    messages.success(request, f"«{request.mark_list.name}» ተባዝቷል።")
    return redirect("school:mark_list_detail", mark_list_id=new_list.pk)


def _mark_list_context(mark_list):
    columns = list(mark_list.columns.all())
    marks = list(
        mark_list.marks.select_related("student").prefetch_related("column_scores")
        .order_by("student__name_key")
    )
    rows = []
    for i, mark in enumerate(marks, start=1):
        by_column = {cs.column_id: cs.score for cs in mark.column_scores.all()}
        rows.append({
            "n": i, "mark": mark, "student": mark.student, "total": mark.total,
            "scores": {c.pk: by_column.get(c.pk) for c in columns},
        })

    enrolled_ids = {m.student_id for m in marks}
    available_students = Student.objects.filter(classroom=mark_list.classroom).exclude(
        pk__in=enrolled_ids
    ).order_by("name_key")

    return {"mark_list": mark_list, "columns": columns, "rows": rows, "available_students": available_students}


@permissions.mark_list_access_required(url_kwarg="mark_list_id")
def mark_list_detail(request, mark_list_id):
    return render(request, "marklists/detail.html", _mark_list_context(request.mark_list))


@permissions.mark_list_access_required(url_kwarg="mark_list_id")
def mark_list_edit_header(request, mark_list_id):
    form = MarkListForm(request.POST or None, instance=request.mark_list)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "የዝርዝሩ መረጃ ተስተካክሏል።")
        return redirect("school:mark_list_detail", mark_list_id=request.mark_list.pk)
    return render(request, "marklists/form.html", {
        "form": form, "classroom": request.mark_list.classroom, "is_new": False, "mark_list": request.mark_list,
    })


@permissions.mark_list_access_required(url_kwarg="mark_list_id")
def add_student(request, mark_list_id):
    mark_list = request.mark_list
    student = get_object_or_404(Student, pk=request.POST.get("student_id"), classroom=mark_list.classroom)
    try:
        services.add_student_to_marklist(mark_list=mark_list, student=student, user=request.user)
    except services.CrossClassError as exc:
        messages.error(request, str(exc))

    if request.htmx:
        return render(request, "partials/_mark_table.html", _mark_list_context(mark_list))
    return redirect("school:mark_list_detail", mark_list_id=mark_list.pk)


@permissions.mark_list_access_required(url_kwarg="mark_list_id")
def column_create(request, mark_list_id):
    mark_list = request.mark_list
    form = MarkColumnForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        column = form.save(commit=False)
        column.mark_list = mark_list
        column.order = mark_list.columns.count()
        column.save()
        for mark in mark_list.marks.all():
            MarkColumnScore.objects.get_or_create(mark=mark, column=column)
        log_action(actor=request.user, action=ActivityLog.Action.CREATE, obj=column, classroom=mark_list.classroom)
    elif request.method == "POST":
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

    if request.htmx:
        table_html = render_to_string(
            request=request, template_name="partials/_mark_table.html", context=_mark_list_context(mark_list)
        )
        flash_html = render_to_string(request=request, template_name="partials/_flash.html", context={})
        return HttpResponse(table_html + f'<div id="flash-container" hx-swap-oob="true">{flash_html}</div>')
    return redirect("school:mark_list_detail", mark_list_id=mark_list.pk)


@permissions.mark_list_access_required(url_kwarg="mark_list_id")
def column_delete(request, mark_list_id, column_id):
    mark_list = request.mark_list
    column = get_object_or_404(MarkColumn, pk=column_id, mark_list=mark_list)
    log_action(actor=request.user, action=ActivityLog.Action.DELETE, obj=column, classroom=mark_list.classroom)
    column.delete()

    if request.htmx:
        return render(request, "partials/_mark_table.html", _mark_list_context(mark_list))
    return redirect("school:mark_list_detail", mark_list_id=mark_list.pk)


def _parse_decimal(raw):
    raw = (raw or "").strip()
    if not raw:
        return None, True
    try:
        return Decimal(raw), True
    except InvalidOperation:
        return None, False


@permissions.mark_list_access_required(url_kwarg="mark_list_id")
def update_cell(request, mark_list_id):
    mark_list = request.mark_list
    mark = get_object_or_404(Mark, pk=request.POST.get("mark_id"), mark_list=mark_list)

    if "total" in request.POST:
        value, ok = _parse_decimal(request.POST["total"])
        if ok:
            services.set_mark_total(mark=mark, total=value, user=request.user)
        else:
            messages.error(request, "ትክክለኛ ቁጥር ያስገቡ።")
    elif "column_id" in request.POST:
        column = get_object_or_404(MarkColumn, pk=request.POST["column_id"], mark_list=mark_list)
        value, ok = _parse_decimal(request.POST.get("score", ""))
        if ok:
            services.set_mark_column_score(mark=mark, column=column, score=value, user=request.user)
        else:
            messages.error(request, "ትክክለኛ ቁጥር ያስገቡ።")

    if request.htmx:
        n = Mark.objects.filter(
            mark_list=mark_list, student__name_key__lt=mark.student.name_key
        ).count() + 1
        by_column = {cs.column_id: cs.score for cs in mark.column_scores.all()}
        row_html = render_to_string(request=request, template_name="partials/_mark_row.html", context={
            "row": {
                "n": n, "mark": mark, "student": mark.student,
                "total": mark.total, "scores": by_column,
            },
            "columns": list(mark_list.columns.all()),
            "oob": True,
        })
        flash_html = render_to_string(request=request, template_name="partials/_flash.html", context={})
        return HttpResponse(
            f"<template>{row_html}</template>"
            f'<div id="flash-container" hx-swap-oob="true">{flash_html}</div>'
        )
    return redirect("school:mark_list_detail", mark_list_id=mark_list.pk)

@permissions.mark_list_access_required(url_kwarg="mark_list_id")
def mark_list_export(request, mark_list_id):
    mark_list = request.mark_list
    context = _mark_list_context(mark_list)
    log_action(actor=request.user, action=ActivityLog.Action.EXPORT, obj=mark_list, classroom=mark_list.classroom)
    return exports.pdf_response("pdf/marklist.html", context, f"marklist-{mark_list.pk}.pdf")