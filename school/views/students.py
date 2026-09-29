from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .. import permissions, services
from ..forms import StudentForm
from ..models import ClassRoom, Student


@login_required
def student_search(request):
    """The live existing-student match check (SRS §4.1/§4.2) — this is completely
    unrelated to the mark-list/roster 'duplicate' actions built elsewhere. htmx
    calls this on every keystroke (debounced client-side) and swaps in the
    fragment below; a full page load here would only happen if JS is off."""
    first = request.GET.get("first_name", "").strip()
    father = request.GET.get("father_name", "").strip()
    grandfather = request.GET.get("grandfather_name", "").strip()

    match = None
    if first and father and grandfather:
        student = services.find_existing_student(first, father, grandfather)
        if student:
            match = {
                "student": student,
                "full_detail": services.can_view_full_match_detail(request.user, student),
            }

    return render(request, "partials/_student_search_results.html", {
        "match": match,
        "searched": bool(first and father and grandfather),
    })


@login_required
def student_register(request):
    """Any authenticated staff member may register into ANY active class,
    not only their own (SRS §4.1.5) — no classroom_access_required here."""
    initial = {}
    for field in ("first_name", "father_name", "grandfather_name"):
        value = request.GET.get(field, "")
        if value:
            initial[field] = value

    form = StudentForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        student = services.register_student(form=form, user=request.user)
        messages.success(request, f"«{student.full_name}» ተመዝግቧል።")
        return redirect("school:student_detail", student_id=student.pk)

    return render(request, "students/register.html", {"form": form})


@login_required
def student_detail(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    if not permissions.can_view_full_student_detail(request.user, student):
        # Same rule as the match-check's reduced view: registered/when/which-class
        # only, for staff outside that student's class — not a hard 403, since the
        # existing-student check already legitimately links here with less detail.
        return render(request, "students/detail_restricted.html", {"student": student})

    return render(request, "students/detail.html", {
        "student": student,
        "can_edit": permissions.can_access_student(request.user, student),
    })


@permissions.student_access_required(url_kwarg="student_id")
@login_required
def student_edit(request, student_id):
    student = request.student  # set by student_access_required
    form = StudentForm(request.POST or None, instance=student)
    if request.method == "POST" and form.is_valid():
        old_classroom = student.classroom
        student = form.save()
        if student.classroom_id != old_classroom.id and not permissions.is_head(request.user):
            # Moving a student to a different class is a Head-only action even
            # though a Leader can otherwise edit students in their own classes —
            # ModelForm.save() would otherwise let this slip through silently.
            messages.error(request, "ተማሪን ወደ ሌላ ክፍል ማዛወር የሚችለው ኃላፊ ብቻ ነው።")
            student.classroom = old_classroom
            student.save()
            return redirect("school:student_detail", student_id=student.pk)

        messages.success(request, "የተማሪ መረጃ ተስተካክሏል።")
        return redirect("school:student_detail", student_id=student.pk)

    return render(request, "students/edit.html", {"form": form, "student": student})