"""Attendance report views + TXT/XLSX export."""
from __future__ import annotations

from io import BytesIO
from urllib.parse import quote

from django.contrib import messages as flash
from django.http import HttpResponse
from django.shortcuts import redirect, render
from openpyxl import Workbook

from lessonix_core.exceptions import DomainError
from lessonix_core.models import Lesson
from lessonix_core.services import attendance as attendance_service

from .common import require_login


@require_login
def teacher_reports_page(request):
    report_names = [
        {"class_name": name}
        for name in request.user_obj.classes.values_list("name", flat=True)
    ]
    return render(request, "lessonixTeacher/teacherreports.html", {"report_names": report_names})


@require_login
def view_class_report(request):
    school = request.school
    selected_class = request.GET.get("class_name")
    selected_subject = request.GET.get("subject_name")

    if request.method == "POST":
        try:
            attendance_service.toggle_status(
                school,
                request.POST.get("class_name"),
                request.POST.get("subject_name"),
                request.POST.get("date"),
                request.POST.get("student_id"),
                request.POST.get("current_status"),
            )
        except DomainError as exc:
            flash.error(request, exc.message)
            return redirect("reports")
        return redirect(
            f"/classreport/?class_name={request.POST.get('class_name')}"
            f"&subject_name={request.POST.get('subject_name')}"
        )

    if not selected_subject:
        subjects = attendance_service.available_subjects(request.user_obj, school, selected_class)
        return render(
            request,
            "lessonixTeacher/subject_selection.html",
            {"selected_class": selected_class, "subjects": subjects, "class_name": selected_class},
        )

    try:
        report_data = attendance_service.class_report(school, selected_class, selected_subject)
    except DomainError as exc:
        flash.error(request, exc.message)
        return redirect("reports")

    return render(
        request,
        "lessonixTeacher/class_report.html",
        {"selected_class": selected_class, "selected_subject": selected_subject, "report_data": report_data},
    )


def _last_lesson(request) -> Lesson | None:
    lesson_id = request.session.get("last_lesson_id")
    if not lesson_id:
        return None
    return Lesson.objects.filter(pk=lesson_id).select_related("school_class", "report").first()


@require_login
def download_txt(request):
    lesson = _last_lesson(request)
    if not lesson:
        return HttpResponse(status=404)

    minutes = seconds = 0
    if lesson.started_at and lesson.ended_at:
        delta = lesson.ended_at - lesson.started_at
        minutes, seconds = int(delta.total_seconds() // 60), int(delta.total_seconds() % 60)

    content = (
        f"Дата уроку: {lesson.date}\n"
        f"Час початку: {lesson.started_at}\n"
        f"Час завершення: {lesson.ended_at}\n"
        f"Тривалість уроку: {minutes} хв {seconds} с\n"
        f"Кабінет: {lesson.cabinet}\n"
        f"Клас: {lesson.class_name}\n"
        f"Предмет: {lesson.subject}\n"
        f"Кількість учнів, які були на уроці: {lesson.present_count}\n"
        f"Кількість учнів, які були відмічені як хворі: {lesson.ill_count}\n"
        f"Кількість учнів, які не були присутніми на уроці: {lesson.absent_count}\n"
    )
    filename = quote(f"{lesson.class_name}_{lesson.subject}_{lesson.date}.txt")
    response = HttpResponse(content, content_type="text/plain")
    response["Content-Disposition"] = f"attachment; filename*=UTF-8''{filename}"
    return response


@require_login
def download_xlsx(request):
    lesson = _last_lesson(request)
    if not lesson:
        return HttpResponse(status=404)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Відвідуваність"
    sheet.append(["Ім'я учня", "Статус"])

    for row in attendance_service.completed_context(lesson)["report_data"]:
        sheet.append([row["full_name"], row["status"]])

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    filename = quote(f"{lesson.class_name}_{lesson.subject}_{lesson.date}.xlsx")
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f"attachment; filename*=UTF-8''{filename}"
    return response
