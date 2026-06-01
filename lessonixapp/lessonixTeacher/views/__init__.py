"""View package.

Re-exports every callable referenced by `urls.py` so the existing
`from . import views; views.home` style keeps working unchanged.
"""
from .auth import authenticate
from .classes import (
    add_to_your_classes,
    class_detail,
    delete_class,
    myclass,
    myclassesPage,
    set_primary_class,
)
from .events import eventAction, eventsPage, singleEventPage
from .home import home, post_message
from .lessons import (
    addCabinet,
    addSubject,
    endLesson,
    generate_qr,
    lessonPage,
    lesson_completed,
    startlessonPage,
)
from .profile import profilePage, student_detail
from .reports import download_txt, download_xlsx, teacher_reports_page, view_class_report
from .school import myschoolPage, schoolclassesPage
from .students import redirect_to_med, update_student_status

__all__ = [
    "authenticate",
    "home",
    "post_message",
    "myschoolPage",
    "schoolclassesPage",
    "myclassesPage",
    "add_to_your_classes",
    "delete_class",
    "class_detail",
    "myclass",
    "set_primary_class",
    "profilePage",
    "student_detail",
    "startlessonPage",
    "lessonPage",
    "generate_qr",
    "endLesson",
    "lesson_completed",
    "addCabinet",
    "addSubject",
    "teacher_reports_page",
    "view_class_report",
    "download_txt",
    "download_xlsx",
    "update_student_status",
    "redirect_to_med",
    "eventsPage",
    "singleEventPage",
    "eventAction",
]
