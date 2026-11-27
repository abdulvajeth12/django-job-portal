# jobs/api_urls.py
from django.urls import path
from .views import (
    job_list_api,
    job_detail_api,
    job_create_api,
    job_update_api,
    job_delete_api,
    register_api,
    login_api,
    profile_api,
    apply_job_api,
    my_applications_api,
)


urlpatterns = [
    # Jobs CRUD (uses api_views.job_list_api so closed jobs are filtered out)
    path('jobs/', job_list_api, name='api_job_list'),
    path('jobs/create/', job_create_api, name='job-create-api'),
    path('jobs/<slug:slug>/', job_detail_api, name='job-detail'),
    path('jobs/<slug:slug>/update/', job_update_api, name='job-update-api'),
    path('jobs/<slug:slug>/delete/', job_delete_api, name='job-delete-api'),

    # Auth
    path('register/', register_api, name='register-api'),
    path('login/', login_api, name='login-api'),

    # Profile & Applications
    path('profile/', profile_api, name='api_profile'),
    path('jobs/<slug:slug>/apply/', apply_job_api, name='api_apply_job'),
    path('my-applications/', my_applications_api, name='api_my_applications'),
]