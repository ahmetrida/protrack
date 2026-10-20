from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_router, name='dashboard_router'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('guide/', views.guide_dashboard, name='guide_dashboard'),
    path('examiner/', views.examiner_dashboard, name='examiner_dashboard'),
    path('admin-portal/', views.admin_dashboard, name='admin_dashboard'),
    path('settings/', views.profile_settings_view, name='profile_settings'),
    path('export-csv/', views.export_department_csv, name='export_department_csv'),
    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('api/check-similarity/', views.api_check_similarity, name='api_check_similarity'),
    path('api/hierarchy/', views.api_hierarchy, name='api_hierarchy'),
]
