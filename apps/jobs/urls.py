from django.urls import path
from . import views

urlpatterns = [
    # Create a new job (POST only)
    path('jobs/', views.PostJobView.as_view(), name='post-job'),
    path('jobs/my-jobs/', views.OrganizationJobListView.as_view(), name='organization-job-list'),
    path('jobs/<int:pk>/', views.JobPostUpdateDeleteView.as_view(), name='job-update-delete'),
    path('jobs/detail/<slug:slug>/', views.JobPostDetailView.as_view(), name='job-detail'),
]