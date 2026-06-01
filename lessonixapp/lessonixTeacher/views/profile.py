"""Teacher profile and single-student profile."""
from __future__ import annotations

from django.contrib import messages as flash
from django.shortcuts import redirect, render

from lessonix_core import repositories as repo
from lessonix_core.exceptions import DomainError
from lessonix_core.services import students as student_service

from .common import require_login


@require_login
def profilePage(request, user_id):
    user = repo.get_user(user_id)
    if not user:
        flash.error(request, "User not found.")
        return redirect("home")
    return render(
        request,
        "lessonixTeacher/profile.html",
        {
            "full_name": user.display_name,
            "subjects": list(user.subjects.values_list("name", flat=True)),
            "classes": list(user.classes.values_list("name", flat=True)),
            "cabinets": list(user.cabinets.values_list("number", flat=True)),
        },
    )


@require_login
def student_detail(request, school_id, student_id):
    school = repo.get_school(school_id) or request.school
    try:
        ctx = student_service.student_detail(school, student_id)
    except DomainError as exc:
        flash.error(request, exc.message)
        return redirect("home")
    return render(request, "lessonixTeacher/singlestudentprofile.html", ctx)
