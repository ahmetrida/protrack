# Force Launch - ProTrack v1.07 Enterprise Edition
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
    path('profile/<str:username>/', views.public_profile_view, name='public_profile'),
    path('export-csv/', views.export_department_csv, name='export_department_csv'),
    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
    # Isolated Superadmin Access Flow
    path('superadmin-access/', views.superadmin_login_view, name='superadmin_login'),
    path('superadmin-console/', views.superadmin_dashboard_view, name='superadmin_dashboard'),
    # APIs
    path('api/check-similarity/', views.api_check_similarity, name='api_check_similarity'),
    path('api/hierarchy/', views.api_hierarchy, name='api_hierarchy'),
    path('api/check-username/', views.api_check_username, name='api_check_username'),
    path('api/search-classmates/', views.api_search_classmates, name='api_search_classmates'),
    path('api/sync-drafts/', views.api_sync_drafts, name='api_sync_drafts'),
]
