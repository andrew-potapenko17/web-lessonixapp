"""Student mobile-app API routes (mounted at /api/student/)."""
from django.urls import path

from . import api

app_name = "student_api"

urlpatterns = [
    path("register", api.register, name="register"),
    path("login", api.login, name="login"),
    path("status", api.status, name="status"),
    path("scan", api.scan, name="scan"),
    path("med", api.med, name="med"),
]
