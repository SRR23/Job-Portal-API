from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegistrationView, 
    ActivateAccountView, 
    LoginView, 
    UserProfileViewSet, 
    PasswordResetRequestView, 
    PasswordResetConfirmView                
)
from rest_framework_simplejwt.views import TokenRefreshView

router = DefaultRouter()
router.register(r'profile', UserProfileViewSet, basename='profile')

urlpatterns = [
    path('register/', RegistrationView.as_view(), name='register'),
    path('activate/<str:token>/', ActivateAccountView.as_view(), name='activate-account'),
    path('login/', LoginView.as_view(), name='login'),
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/<str:token>/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]

# http://localhost:8000/api/profile/  use to see user profile
# http://localhost:8000/api/profile/29/ put, patch, delete