from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('api/check-similarity/', views.api_check_similarity, name='api_check_similarity'),
    path('api/notifications/read/', views.api_mark_notifications_read, name='api_mark_notifications_read'),
    path('submit-proposal/', views.submit_proposal, name='submit_proposal'),
    path('add-log/', views.add_weekly_log, name='add_weekly_log'),
    path('upload-final/', views.upload_final_submission, name='upload_final_submission'),
    path('review-proposal/<int:proposal_id>/', views.review_proposal, name='review_proposal'),
    path('review-log/<int:log_id>/', views.review_log, name='review_log'),
    path('submit-viva/<int:group_id>/', views.submit_viva_marks, name='submit_viva_marks'),
    path('export-csv/', views.export_marksheet_csv, name='export_marksheet_csv'),
]
