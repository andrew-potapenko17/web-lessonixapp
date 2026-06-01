"""Student status changes and medical-office routing."""
from __future__ import annotations

from django.contrib import messages as flash
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render

from lessonix_core.exceptions import DomainError
from lessonix_core.services import students as student_service

from .common import require_login


@require_login
def update_student_status(request, student_id, new_status):
    try:
        student_service.update_status(request.user_obj, request.school, student_id, new_status)
    except DomainError as exc:
        flash.error(request, exc.message)
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@require_login
def redirect_to_med(request, student_id):
    if request.method == "POST":
        try:
            student_service.send_to_med(request.school, student_id, request.POST.get("reason", ""))
        except DomainError as exc:
            flash.error(request, exc.message)
        return redirect("lesson")
    return render(request, "lessonixTeacher/gomedpage.html", {"student_id": student_id})
