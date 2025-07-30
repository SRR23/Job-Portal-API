from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegistrationView, ActivateAccountView, LoginView, UserProfileViewSet
from rest_framework_simplejwt.views import TokenRefreshView

router = DefaultRouter()
router.register(r'profile', UserProfileViewSet, basename='profile')

urlpatterns = [
    path('register/', RegistrationView.as_view(), name='register'),
    path('activate/<str:token>/', ActivateAccountView.as_view(), name='activate-account'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]