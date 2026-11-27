from django.urls import path
from . import views  # We will define views next

urlpatterns = [
    path('', views.jobs_list, name='jobs_list'),
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('register/', views.register_view, name='register'),
    path("job/<slug:slug>/", views.job_details, name="job_details"),
    path("add-job/", views.add_job, name="add_job"),
    path("edit-job/<slug:slug>/", views.edit_job, name="edit_job"),
    path("delete-job/<slug:slug>/", views.delete_job, name="delete_job"),
    path('job/<slug:slug>/apply/', views.apply_job, name='apply_job'),
    path('my-applications/', views.my_applications, name='my_applications'),
    path('employer/dashboard/', views.employer_dashboard, name='employer_dashboard'),
    path('employer/job/<slug:slug>/applicants/', views.job_applicants, name='job_applicants'),
    path('profile/', views.profile_view, name='profile_view'),
    path('employer/job/<slug:slug>/toggle/', views.toggle_job_status, name='toggle_job_status'),
]