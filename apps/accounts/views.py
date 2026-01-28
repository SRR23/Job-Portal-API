import logging
from django.conf import settings
from celery.exceptions import OperationalError
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.permissions import IsAuthenticated
from .models import User
from .serializers import (
    RegistrationSerializer, 
    UserProfileSerializer, 
    PasswordResetRequestSerializer, 
    PasswordResetConfirmSerializer
)
from django.urls import reverse
from django.shortcuts import redirect
import jwt
import datetime
from .tasks import (
    send_activation_email, 
    send_password_reset_email
)

# Configure logging
logger = logging.getLogger(__name__)

class RegistrationView(APIView):
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Registration failed due to serializer errors: {serializer.errors}")
            return Response(
                {"status": "error", "message": "Invalid registration data.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create inactive user
            user = serializer.save(is_active=False)
            logger.info(f"User created with id={user.id}, email={user.email}")

            # Generate activation token (expires in 24 hours)
            expiration_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
            token = jwt.encode(
                {"user_id": user.id, "exp": expiration_time},
                settings.SECRET_KEY,
                algorithm="HS256"
            )

            # Generate activation URL dynamically
            activation_url = request.build_absolute_uri(reverse('activate-account', args=[token]))
            logger.debug(f"Activation URL generated: {activation_url}")

            # Send activation email via Celery
            try:
                task = send_activation_email.delay(user.id, activation_url, user.email)
                logger.info(f"Activation email task queued for user_id={user.id}, email={user.email}, task_id={task.id}")
            except OperationalError as e:
                logger.error(f"Failed to queue activation email task for user_id={user.id}, email={user.email}: {str(e)}")
                user.delete()  # Rollback user creation
                return Response(
                    {"status": "error", "message": "Failed to connect to task queue. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(
                {"status": "success", "message": "User registered. Check your email to activate your account."},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Unexpected error during registration for email={request.data.get('email')}: {str(e)}")
            return Response(
                {"status": "error", "message": "An unexpected error occurred during registration."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

class ActivateAccountView(APIView):
    def get(self, request, token):
        try:
            # Decode the token
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user = User.objects.get(id=payload["user_id"])
            
            if user.is_active:
                logger.warning(f"Account already activated for user_id={user.id}, email={user.email}")
                return Response(
                    {"status": "error", "message": "Account already activated."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Activate the user account
            user.is_active = True
            user.save()
            logger.info(f"Account activated successfully for user_id={user.id}, email={user.email}")
            
            # Redirect to frontend login page
            return redirect('/')

        except jwt.ExpiredSignatureError:
            logger.warning(f"Activation token expired for token={token}")
            return Response(
                {"status": "error", "message": "Activation link has expired."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except (jwt.DecodeError, User.DoesNotExist) as e:
            logger.error(f"Invalid activation attempt with token={token}: {str(e)}")
            return Response(
                {"status": "error", "message": "Invalid activation token or user does not exist."},
                status=status.HTTP_400_BAD_REQUEST
            )
    

class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, email=email, password=password)

        if user:
            if not user.is_active:
                logger.warning(f"Login attempt for inactive account: email={email}")
                return Response(
                    {"status": "error", "message": "Account is not activated. Please check your email."},
                    status=status.HTTP_403_FORBIDDEN
                )

            refresh = RefreshToken.for_user(user)
            user_data = UserProfileSerializer(user).data
            logger.info(f"Successful login for user_id={user.id}, email={email}")

            response = Response(
                {
                    "status": "success",
                    "user": user_data,
                    "access_token": str(refresh.access_token),  # frontend will use this
                },
                status=status.HTTP_200_OK
            )

            # Store refresh token in HttpOnly cookie
            response.set_cookie(
                key="refresh_token",
                value=str(refresh),
                httponly=True,
                secure=False,      # only True for HTTPS in production
                samesite="Lax",
                max_age=7 * 24 * 60 * 60  # 7 days
            )

            return response

        logger.warning(f"Failed login attempt for email={email}: Invalid credentials")
        return Response(
            {"status": "error", "message": "Invalid email or password."},
            status=status.HTTP_401_UNAUTHORIZED
        )
    

class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token")

        if not refresh_token:
            return Response({"error": "Refresh token missing"}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = self.get_serializer(data={"refresh": refresh_token})
        serializer.is_valid(raise_exception=True)

        access = serializer.validated_data["access"]

        return Response({"access_token": access}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = Response(
            {"status": "success", "message": "Logged out successfully."},
            status=status.HTTP_200_OK
        )
        # Remove refresh cookie
        response.delete_cookie("refresh_token")
        return response

    

class UserProfileViewSet(viewsets.ModelViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)

    def perform_update(self, serializer):
        try:
            serializer.save()
            logger.info(f"User profile updated for user_id={self.request.user.id}")
        except Exception as e:
            logger.error(f"Failed to update user profile for user_id={self.request.user.id}: {str(e)}")
            raise


class PasswordResetRequestView(APIView):
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"status": "error", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)
            
            # Generate password reset token (expires in 1 hour)
            expiration_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
            token = jwt.encode(
                {
                    "user_id": user.id,
                    "exp": expiration_time,
                    "type": "password_reset"  # Differentiate from activation token
                },
                settings.SECRET_KEY,
                algorithm="HS256"
            )

            # Generate reset URL
            reset_url = request.build_absolute_uri(reverse('password-reset-confirm', args=[token]))
            logger.info(f"Password reset URL generated for user_id={user.id}: {reset_url}")

            # Send password reset email via Celery
            try:
                task = send_password_reset_email.delay(user.id, reset_url, user.email)
                logger.info(f"Password reset email task queued for user_id={user.id}, task_id={task.id}")
            except OperationalError as e:
                logger.error(f"Failed to queue password reset email for user_id={user.id}: {str(e)}")
                return Response(
                    {"status": "error", "message": "Failed to connect to email service. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(
                {"status": "success", "message": "Password reset link sent to your email."},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error in password reset request for email={email}: {str(e)}")
            return Response(
                {"status": "error", "message": "An error occurred while processing your request."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PasswordResetConfirmView(APIView):
    def post(self, request, token):
         # Combine URL token with request data
        data = request.data.copy()
        data['token'] = token
        
        serializer = PasswordResetConfirmSerializer(data=data)
        if not serializer.is_valid():
            return Response(
                {"status": "error", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify token
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            
            # Additional token validation
            if payload.get('type') != 'password_reset':
                raise jwt.InvalidTokenError("Invalid token type")
            
            user = User.objects.get(id=payload['user_id'])
            
            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            logger.info(f"Password reset successfully for user_id={user.id}")

            return Response(
                {"status": "success", "message": "Password has been reset successfully."},
                status=status.HTTP_200_OK
            )

        except jwt.ExpiredSignatureError:
            logger.warning(f"Expired password reset token: {token}")
            return Response(
                {"status": "error", "message": "Password reset link has expired."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except (jwt.DecodeError, jwt.InvalidTokenError, User.DoesNotExist) as e:
            logger.error(f"Invalid password reset token: {token}, error: {str(e)}")
            return Response(
                {"status": "error", "message": "Invalid or corrupted password reset link."},
                status=status.HTTP_400_BAD_REQUEST
            )