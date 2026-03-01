from django.contrib.auth import get_user_model
from rest_framework import generics, status

User = get_user_model()
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.views import APIView

from .serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer,
    ChangePasswordSerializer, AdminUserSerializer,
    RequestPasswordResetSerializer, ConfirmPasswordResetSerializer
)
from .models import PasswordResetToken
from .services import AuthService
import secrets
from django.core.mail import send_mail
from django.conf import settings


class RegisterView(generics.CreateAPIView):
    """Register a new user account."""
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        print(f"DEBUG: Registration request data: {request.data}")
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            print(f"DEBUG: Registration validation failed: {serializer.errors}")
            raise e
        tokens, user = AuthService.register_user(serializer.validated_data)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Authenticate user and return JWT tokens."""
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens, user = AuthService.login_user(
            serializer.validated_data['username'],
            serializer.validated_data['password'],
        )
        if tokens is None:
            return Response(
                {'detail': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
        })


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get or update the current user's profile."""
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """Update password for the current user."""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'old_password': ['Wrong password.']}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'detail': 'Password updated successfully.'}, status=status.HTTP_200_OK)


class UserManagementView(generics.ListCreateAPIView):
    """Admin-only: List or Create users (including other admins)."""
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = AdminUserSerializer
    permission_classes = (IsAuthenticated, IsAdminUser)

    def get_queryset(self):
        # Admins can see everyone
        return User.objects.all().order_by('-date_joined')


class UserDetailManagementView(generics.RetrieveUpdateDestroyAPIView):
    """Admin-only: Manage a specific user."""
    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = (IsAuthenticated, IsAdminUser)


class RequestPasswordResetView(APIView):
    """Request a password reset PIN via email."""
    permission_classes = (AllowAny,)

    def post(self, request):
        try:
            serializer = RequestPasswordResetSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            email = serializer.validated_data['email']

            user = User.objects.filter(email=email).first()
            if not user:
                return Response({'email': ['No account is associated with this email address.']}, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate 6-digit PIN
            token = "".join(secrets.choice("0123456789") for _ in range(6))
            
            # Invalidate old tokens
            PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)
            
            # Create new token
            PasswordResetToken.objects.create(user=user, token=token)
            
            # Send email
            frontend_url = request.META.get('HTTP_ORIGIN', 'http://localhost:5173')
            magic_link = f"{frontend_url}/forgot-password?token={token}&email={user.email}"
            
            subject = 'ByteSlot - Password Reset'
            message = f'Hello {user.first_name or "User"},\n\nClick the link below to securely reset your password:\n{magic_link}\n\nThis link will expire in 15 minutes.\n\nRegards,\nThe ByteSlot Team'
            
            print(f"\n{'='*40}")
            print(f"MAGIC LINK FOR {user.email}: \n{magic_link}")
            print(f"{'='*40}\n")
            
            try:
                from core.models import SystemSettings
                from django.core.mail import get_connection
                settings_db = SystemSettings.load()
                from_email = settings_db.default_from_email or settings.DEFAULT_FROM_EMAIL
                
                if settings_db.email_host_user and settings_db.email_host_password:
                    connection = get_connection(
                        host=settings_db.email_host,
                        port=settings_db.email_port,
                        username=settings_db.email_host_user,
                        password=settings_db.email_host_password,
                        use_tls=settings_db.email_use_tls,
                    )
                    send_mail(subject, message, from_email, [user.email], fail_silently=False, connection=connection)
                else:
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
            except Exception as e:
                print(f"SMTP Error during password reset: {e}")
                # We don't return 500 here so the user can still use the console fallback for local testing!
            
            return Response({'detail': 'Password reset code sent.'}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error in password reset request: {e}")
            return Response({'detail': 'Failed to send reset email. Ensure your email server settings are correct.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ConfirmPasswordResetView(APIView):
    """Verify PIN and set new password."""
    permission_classes = (AllowAny,)

    def post(self, request):
        try:
            serializer = ConfirmPasswordResetSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            email = serializer.validated_data['email']
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']

            user = User.objects.filter(email=email).first()
            if not user:
                return Response({'detail': 'Invalid email or reset code.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                reset_token = PasswordResetToken.objects.get(user=user, token=token, is_used=False)
            except PasswordResetToken.DoesNotExist:
                return Response({'detail': 'Invalid email or reset code.'}, status=status.HTTP_400_BAD_REQUEST)

            if reset_token.is_expired():
                return Response({'detail': 'Reset code has expired.'}, status=status.HTTP_400_BAD_REQUEST)

            # Update password
            user.set_password(new_password)
            user.save()

            # Mark token as used
            reset_token.is_used = True
            reset_token.save()

            return Response({'detail': 'Password reset successful.'}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error in password reset confirm: {e}")
            return Response({'detail': 'An unexpected error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
