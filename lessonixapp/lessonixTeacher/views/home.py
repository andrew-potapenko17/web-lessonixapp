"""Home dashboard + community message posting."""
from __future__ import annotations

from django.contrib import messages as flash
from django.shortcuts import redirect, render

from lessonix_core.exceptions import DomainError
from lessonix_core.services import messages as message_service

from .common import require_login


@require_login
def home(request):
    recent = message_service.recent(request.school, limit=20) if request.school else []
    return render(request, "lessonixTeacher/home.html", {"messagesc": recent})


@require_login
def post_message(request):
    if request.method != "POST":
        flash.error(request, "Invalid request method.")
        return redirect("home")
    try:
        message_service.post(request.user_obj, request.school, request.POST.get("message"))
        flash.success(request, "Message sent successfully!")
    except DomainError as exc:
        flash.error(request, exc.message)
    return redirect("home")
