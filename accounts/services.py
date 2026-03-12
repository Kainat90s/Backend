from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class AuthService:
    """Business logic for authentication."""

    @staticmethod
    def register_user(validated_data):
        """Create a new user and return JWT tokens."""
        if validated_data.get('email') and not validated_data.get('username'):
            validated_data['username'] = validated_data['email']
        user = User.objects.create_user(**validated_data)
        return AuthService._get_tokens(user), user

    @staticmethod
    def login_user(email, password):
        """Authenticate user by email and return JWT tokens."""
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            return None, None
        if not user.check_password(password):
            return None, None
        if not user.is_active:
            return None, None
        return AuthService._get_tokens(user), user

    @staticmethod
    def _get_tokens(user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
