from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('med/', include('lessonix_med.urls')),
    path('auth/', include('authentication.urls')),
    path('', include('lessonix.urls')),
]
