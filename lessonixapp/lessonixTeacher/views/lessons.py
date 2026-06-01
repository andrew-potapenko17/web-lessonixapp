"""Lesson lifecycle views: start, run (QR), end, completed, catalogue add."""
from __future__ import annotations

from django.contrib import messages as flash
from django.http import JsonResponse
from django.shortcuts import redirect, render

from lessonix_core import qr as qr_util
from lessonix_core import repositories as repo
from lessonix_core.exceptions import DomainError
from lessonix_core.models import Lesson
from lessonix_core.services import attendance as attendance_service
from lessonix_core.services import lessons as lesson_service
from lessonix_core.services import subjects as subject_service

from .common import require_login


@require_login
def startlessonPage(request):
    user = request.user_obj
    if lesson_service.has_active_lesson(user):
        return redirect("lesson")

    if request.method == "POST":
        try:
            lesson_service.start_lesson(
                user,
                request.school,
                request.POST.get("class"),
                request.POST.get("cabinet"),
                request.POST.get("subject"),
            )
            return redirect("lesson")
        except DomainError as exc:
            flash.error(request, exc.message)

    return render(request, "lessonixTeacher/startlessonpage.html", lesson_service.start_context(user))


@require_login
def lessonPage(request):
    lesson = lesson_service.current_lesson(request.user_obj, request.school)
    if not lesson:
        return redirect("start_lesson_page")

    qr_hash = repo.random_hash()
    lesson_service.set_qr_hash(lesson, qr_hash)
    return render(
        request,
        "lessonixTeacher/lesson.html",
        {
            "class_name": lesson.class_name,
            "subject": lesson.subject,
            "cabinet": lesson.cabinet,
            "school_id": request.school.code if request.school else "",
            "lessonID": lesson.uid,
            "qr_code": qr_util.lesson_qr(lesson.uid, qr_hash),
        },
    )


@require_login
def lesson_students(request):
    """JSON: students of the active lesson (polled by lesson.js, replaces Firebase)."""
    return JsonResponse({"students": lesson_service.live_students(request.user_obj, request.school)})


@require_login
def generate_qr(request, lessonID):
    lesson = repo.get_active_lesson(request.school, lessonID)
    if not lesson:
        return JsonResponse({"error": "Lesson not found"}, status=404)
    qr_hash = repo.random_hash()
    lesson_service.set_qr_hash(lesson, qr_hash)
    return JsonResponse({"qr_code": qr_util.lesson_qr(lessonID, qr_hash)})


@require_login
def endLesson(request):
    try:
        lesson = lesson_service.end_lesson(request.user_obj, request.school)
        if lesson:
            request.session["last_lesson_id"] = lesson.pk
        flash.success(request, "Lesson ended successfully.")
    except DomainError as exc:
        flash.error(request, exc.message)
    return redirect("lesson_completed")


@require_login
def lesson_completed(request):
    lesson_id = request.session.get("last_lesson_id")
    lesson = Lesson.objects.filter(pk=lesson_id).select_related("school_class", "report").first() if lesson_id else None
    if not lesson:
        flash.error(request, "No lesson completion data found.")
        return redirect("home")
    return render(request, "lessonixTeacher/lessoncompleted.html", attendance_service.completed_context(lesson))


@require_login
def addCabinet(request):
    if request.method == "POST":
        try:
            subject_service.add_cabinet(request.user_obj, request.POST.get("cab_num"))
            request.session["cabs"] = list(request.user_obj.cabinets.values_list("number", flat=True))
            flash.success(request, "Cabinet added to your cabinets.")
            return redirect("start_lesson_page")
        except DomainError as exc:
            flash.info(request, exc.message)
    return render(request, "lessonixTeacher/addcabinet.html")


@require_login
def addSubject(request):
    if request.method == "POST":
        try:
            subject_service.add_subject(request.user_obj, request.POST.get("subject_name"))
            request.session["subjects"] = list(request.user_obj.subjects.values_list("name", flat=True))
            flash.success(request, "Subject added to your subjects.")
            return redirect("start_lesson_page")
        except DomainError as exc:
            flash.info(request, exc.message)
    return render(request, "lessonixTeacher/addsubject.html")
