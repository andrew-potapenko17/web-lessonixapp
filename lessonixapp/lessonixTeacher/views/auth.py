"""Token hand-off endpoint: verify the JWT from the auth service, open a session."""
from __future__ import annotations

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect

from lessonix_core.exceptions import DomainError
from lessonix_core.services import auth as auth_service


def authenticate(request):
    token = request.GET.get("token")
    try:
        user = auth_service.user_from_token(token)
    except DomainError as exc:
        return JsonResponse({"error": exc.message}, status=exc.status_code)

    for key, value in auth_service.session_payload(user).items():
        request.session[key] = value

    messages.success(request, "Successfully logged in")
    return redirect("home")
