"""Shared view helpers: auth guard, current user/school, error handling."""
from __future__ import annotations

import functools

from django.contrib import messages
from django.shortcuts import redirect

from lessonix_core import repositories as repo
from lessonix_core.exceptions import DomainError


def current_user(request):
    uid = request.session.get("user_id")
    return repo.get_user(uid) if uid else None


def require_login(view):
    """Attach `request.user_obj` / `request.school` or bounce to /authenticate."""

    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        user = current_user(request)
        if not user:
            messages.error(request, "User not logged in. Please log in again.")
            return redirect("authenticate")
        request.user_obj = user
        request.school = user.school
        return view(request, *args, **kwargs)

    return wrapper


def flash_domain_error(request, exc: DomainError) -> None:
    """Surface a domain error to the user as a flash message."""
    messages.error(request, exc.message)
