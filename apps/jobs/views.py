

from rest_framework.generics import RetrieveAPIView, ListAPIView, DestroyAPIView
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
    AllowAny,
)
from rest_framework.exceptions import ValidationError
from django.db.models import Q, Exists, OuterRef
from rest_framework.response import Response
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.conf import settings
from rest_framework import status, pagination
from rest_framework.views import APIView

from .models import (
    Category, 
    Tag,
    Job,
)
from .serializers import (
    CategorySerializer,
    TagSerializer,
    OrganizationSerializer,
    JobSerializer,
    ApplicationSerializer,
    
)


# Custom pagination class
class PaginationView(pagination.PageNumberPagination):
    page_size = 9  # Default page size
    page_size_query_param = 'page_size'

    def get_max_page_size(self, total_records):
        """Dynamically set max page size based on total records."""
        return max(50, total_records // 9)  # Ensures at least 50

    def paginate_queryset(self, queryset, request, view=None):
        total_records = len(queryset)  # Total data count
        self.max_page_size = self.get_max_page_size(total_records)  # Set max dynamically
        return super().paginate_queryset(queryset, request, view)
    
    def get_paginated_response(self, data):
        """Customize paginated response to include page links."""
        return Response({
            "count": self.page.paginator.count,  # Total items
            "total_pages": self.page.paginator.num_pages,  # Total pages
            "current_page": self.page.number,  # Current page number
            "page_size": self.page.paginator.per_page,  # Items per page
            "next": self.get_next_link(),  # Next page URL
            "previous": self.get_previous_link(),  # Previous page URL
            "results": data  # Paginated results
        })

# List all Categories
class CategoryListView(ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer 


class PostJobView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "organization":  # Only owners can add flats
            return Response(
                {"error": "Only Organization can post Jobs"}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = JobSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrganizationJobListView(ListAPIView):
    """List all flats added by the logged-in owner"""

    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.role != "organization":
            return Job.objects.none()  # Return an empty queryset instead of filtering

        return (
            Job.objects.filter(organization=user)
            .select_related("organization","category")
            .prefetch_related("tags", "jobSeekers_who_apply")
            .order_by("-created_at")  # Show newest job first
        )

    def list(self, request, *args, **kwargs):
        if request.user.role != "organization":
            return Response(
                {"error": "Only organization can view their jobs"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().list(request, *args, **kwargs)


# Update and Delete job posts
class JobPostUpdateDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        """Helper method to get job object and check ownership."""
        try:
            job = Job.objects.get(pk=pk)
            if job.organization != user or user.role != "organization":
                raise ValidationError({"error": "You do not have permission to modify this job."})
            return job
        except Job.DoesNotExist:
            raise ValidationError({"error": "Job not found."})

    def patch(self, request, pk):
        """Handle updating a job post."""
        if request.user.role != "organization":
            return Response(
                {"error": "Only organization can update their jobs"},
                status=status.HTTP_403_FORBIDDEN,
            )
        job = self.get_object(pk, request.user)
        serializer = JobSerializer(job, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Handle deleting a job post."""
        if request.user.role != "organization":
            return Response(
                {"error": "Only organization can delete their jobs"},
                status=status.HTTP_403_FORBIDDEN,
            )
        job = self.get_object(pk, request.user)
        job.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Retrieve details of a specific job post
class JobPostDetailView(RetrieveAPIView):
    queryset = Job.objects.select_related(
        "organization", "category"
    ).prefetch_related("tags", "jobSeekers_who_apply")
    serializer_class = JobSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # Anyone can view, but modifications require authentication
    lookup_field = "slug"  # Retrieve job details using the slug

