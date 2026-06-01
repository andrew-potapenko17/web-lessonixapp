"""Event views: list/create, detail (with QR), start/finish action."""
from __future__ import annotations

from django.contrib import messages as flash
from django.shortcuts import redirect, render

from lessonix_core import qr as qr_util
from lessonix_core.exceptions import DomainError
from lessonix_core.models import EventState
from lessonix_core.services import events as event_service

from .common import require_login

_ACTION_LABEL = {
    EventState.NOT_STARTED: "Розпочати захід",
    EventState.RUNNING: "Завершити захід",
    EventState.FINISHED: "Захід завершено",
}


@require_login
def eventsPage(request):
    user, school = request.user_obj, request.school

    if request.method == "POST":
        try:
            event_service.create(
                user, school,
                request.POST.get("topic"),
                request.POST.get("cabinet"),
                request.POST.get("time"),
            )
            request.session["events"] = list(user.events.values_list("uid", flat=True))
        except DomainError as exc:
            flash.error(request, exc.message)
        return redirect("events")

    return render(
        request,
        "lessonixTeacher/events.html",
        {
            "user_cabs": list(user.cabinets.values_list("number", flat=True)),
            "user_events": event_service.list_for_user(user, school),
        },
    )


@require_login
def singleEventPage(request, eventHash):
    try:
        event = event_service.detail(request.school, eventHash)
    except DomainError as exc:
        flash.error(request, exc.message)
        return redirect("events")

    qr_code = ""
    if event.state == EventState.RUNNING:
        qr_code = qr_util.event_qr(event.uid, event.cabinet, request.school.code)

    persons = list(event.participants.values_list("display_name", flat=True))
    return render(
        request,
        "lessonixTeacher/eventPage.html",
        {
            "name": event.topic,
            "started": event.get_state_display(),
            "actionButton": _ACTION_LABEL.get(event.state, "EVENT_ACTION"),
            "time": event.time or "Unknown",
            "hash": event.uid,
            "qr_code": qr_code,
            "persons": persons,
        },
    )


@require_login
def eventAction(request, eventHash):
    try:
        event_service.advance_state(request.user_obj, request.school, eventHash)
    except DomainError as exc:
        flash.error(request, exc.message)
    return redirect("eventPage", eventHash)
