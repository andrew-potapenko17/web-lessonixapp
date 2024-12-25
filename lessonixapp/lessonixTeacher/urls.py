from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('authenticate/', views.authenticate, name='authenticate'),
    path('myschool/', views.myschoolPage, name='my_school'),
    path('myclasses/', views.myclassesPage, name='my_classes'),
    path('reports/', views.teacher_reports_page, name='reports'),
    path('schoolclasses/', views.schoolclassesPage, name='schoolclasses'),
    path('add_to_your_classes/<str:class_name>/', views.add_to_your_classes, name='add_to_your_classes'),
    path('profile/<str:user_id>/', views.profilePage, name='profile'),
    path('class/<str:schoolID>/<str:name>/', views.class_detail, name='class_detail'),
    path('student/<str:school_id>/<str:student_id>/', views.student_detail, name='student_detail'),
    path('startlesson/', views.startlessonPage, name='start_lesson_page'),
    path('lesson/', views.lessonPage, name='lesson'),
    path('addcabinet/', views.addCabinet, name='add_cabinet'),
    path('addsubject/', views.addSubject, name='add_subject'),
    path('redirect_med/<str:student_id>/', views.redirect_to_med, name='redirect_med'),
    path('end-lesson/', views.endLesson, name='end_lesson'),
    path('classreport/', views.view_class_report, name='view_class_report'),
    path('update_status/<str:student_id>/<str:new_status>/', views.update_student_status, name='update_status'),
    path('set_primary_class/<str:school_id>/<str:class_name>/', views.set_primary_class, name='set_primary_class'),
    path('myclass/', views.myclass, name='myclass'),
    path('lessoncompleted/', views.lesson_completed, name="lesson_completed"),
    path('sendmessage/', views.post_message, name="post_message"),
    path('download_txt/', views.download_txt, name='download_txt'),
    path('download_xlsx/', views.download_xlsx, name='download_xlsx'),
    path('delete_class/<str:class_name>/', views.delete_class, name='del_class'),
    path('events/', views.eventsPage, name='events'),
    path('event/<str:eventHash>/', views.singleEventPage, name='eventPage'),
    path('eventaction/<str:eventHash>/', views.eventAction, name='eventAction'),
]
