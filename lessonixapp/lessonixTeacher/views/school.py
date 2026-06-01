"""School-wide pages: staff list and all classes."""
from __future__ import annotations

from django.shortcuts import render

from lessonix_core.services import classes as class_service
from lessonix_core.services import schools as school_service

from .common import require_login


@require_login
def myschoolPage(request):
    school = request.school
    return render(
        request,
        "lessonixTeacher/myschool.html",
        {
            "school_name": school_service.school_name(school),
            "users": school_service.staff_members(school) if school else [],
        },
    )


@require_login
def schoolclassesPage(request):
    school = request.school
    return render(
        request,
        "lessonixTeacher/schoolclasses.html",
        {
            "classes": class_service.school_classes(school) if school else [],
            "school_id": school.code if school else "",
            "school_name": school_service.school_name(school),
        },
    )
