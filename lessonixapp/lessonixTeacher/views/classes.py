"""Class membership and detail views."""
from __future__ import annotations

from django.contrib import messages as flash
from django.shortcuts import redirect, render

from lessonix_core.exceptions import DomainError
from lessonix_core.services import classes as class_service

from .common import require_login


@require_login
def myclassesPage(request):
    school = request.school
    classes = class_service.teacher_classes(request.user_obj)
    return render(
        request,
        "lessonixTeacher/myclasses.html",
        {"classes": classes, "school_id": school.code if school else ""},
    )


@require_login
def add_to_your_classes(request, class_name):
    try:
        class_service.follow_class(request.user_obj, class_name)
        request.session["classes"] = list(request.user_obj.classes.values_list("name", flat=True))
        flash.success(request, f"Class '{class_name}' added to your classes.")
    except DomainError as exc:
        flash.info(request, exc.message)
    return redirect("my_classes")


@require_login
def delete_class(request, class_name):
    try:
        class_service.unfollow_class(request.user_obj, class_name)
        request.session["classes"] = list(request.user_obj.classes.values_list("name", flat=True))
        flash.success(request, f"Class '{class_name}' removed from your classes.")
    except DomainError as exc:
        flash.error(request, exc.message)
    return redirect("my_classes")


@require_login
def class_detail(request, schoolID, name):
    from lessonix_core import repositories as repo

    school = repo.get_school(schoolID) or request.school
    try:
        ctx = class_service.class_detail(school, name)
    except DomainError as exc:
        flash.error(request, exc.message)
        ctx = {"class_name": name, "school_id": schoolID, "students": []}
    return render(request, "lessonixTeacher/class_detail.html", ctx)


@require_login
def myclass(request):
    try:
        ctx = class_service.primary_class_detail(request.user_obj)
    except DomainError as exc:
        flash.error(request, exc.message)
        ctx = {"class_name": None, "school_id": request.school.code if request.school else "", "students": []}
    return render(request, "lessonixTeacher/myclass.html", ctx)


@require_login
def set_primary_class(request, school_id, class_name):
    from lessonix_core import repositories as repo

    school = repo.get_school(school_id) or request.school
    try:
        class_service.set_primary_class(request.user_obj, school, class_name)
    except DomainError as exc:
        flash.error(request, exc.message)
    return redirect("class_detail", schoolID=school_id, name=class_name)
