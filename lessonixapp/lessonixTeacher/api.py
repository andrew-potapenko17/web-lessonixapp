"""JSON API for the student mobile app.

Stateless, Bearer-JWT authenticated (the same JWT the auth service issues).
All endpoints return JSON; domain errors map to the right HTTP status.

Routes (see api_urls.py), all under /api/student/:
    POST  register   {register_code, email, password}      -> profile + token
    POST  login      {email, password}                     -> profile + token
    GET   status                                           -> {school_status, student_status, lesson}
    POST  scan       {lessonID, qrhash}                     -> {student_status, message}
    POST  med        {reason}                               -> {student_status}
"""
from __future__ import annotations

import functools
import json

import jwt
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from lessonix_core import repositories as repo
from lessonix_core import security
from lessonix_core.exceptions import DomainError, NotAuthenticated, TokenInvalid
from lessonix_core.services import student as student_service


# --------------------------------------------------------------------------- #
#  Plumbing
# --------------------------------------------------------------------------- #
def _json_body(request) -> dict:
    if not request.body:
        return {}
    try:
        data = json.loads(request.body.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (ValueError, UnicodeDecodeError):
        return {}


def _error(exc: DomainError) -> JsonResponse:
    return JsonResponse({"error": exc.message, "code": exc.code}, status=exc.status_code)


def _user_from_bearer(request):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise NotAuthenticated("Authorization Bearer token required")
    token = header[len("Bearer "):].strip()
    try:
        payload = security.decode_token(token)
    except jwt.PyJWTError as exc:
        raise TokenInvalid(str(exc)) from exc
    user = repo.get_user_by_email(payload.get("email", ""))
    if not user:
        raise NotAuthenticated("User not found")
    return user


def api_view(*, auth_required: bool):
    """Decorator: JSON error handling + optional Bearer auth (sets request.user_obj)."""

    def decorator(view):
        @csrf_exempt
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            try:
                if auth_required:
                    request.user_obj = _user_from_bearer(request)
                return view(request, *args, **kwargs)
            except DomainError as exc:
                return _error(exc)
            except Exception as exc:  # noqa: BLE001 - last-resort guard
                return JsonResponse({"error": str(exc), "code": "server_error"}, status=500)

        return wrapper

    return decorator


# --------------------------------------------------------------------------- #
#  Endpoints
# --------------------------------------------------------------------------- #
@require_http_methods(["POST"])
@api_view(auth_required=False)
def register(request):
    body = _json_body(request)
    data = student_service.register(
        body.get("register_code"), body.get("email"), body.get("password")
    )
    return JsonResponse(data, status=201)


@require_http_methods(["POST"])
@api_view(auth_required=False)
def login(request):
    body = _json_body(request)
    data = student_service.login(body.get("email"), body.get("password"))
    return JsonResponse(data, status=200)


@require_http_methods(["GET"])
@api_view(auth_required=True)
def status(request):
    return JsonResponse(student_service.status(request.user_obj), status=200)


@require_http_methods(["POST"])
@api_view(auth_required=True)
def scan(request):
    body = _json_body(request)
    data = student_service.scan_qr(request.user_obj, body.get("lessonID"), body.get("qrhash"))
    return JsonResponse(data, status=200)


@require_http_methods(["POST"])
@api_view(auth_required=True)
def med(request):
    body = _json_body(request)
    data = student_service.go_med(request.user_obj, body.get("reason"))
    return JsonResponse(data, status=200)
