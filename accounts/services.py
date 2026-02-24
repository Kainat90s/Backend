from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class AuthService:
    """Business logic for authentication."""

    @staticmethod
    def register_user(validated_data):
        """Create a new user and return JWT tokens."""
        user = User.objects.create_user(**validated_data)
        return AuthService._get_tokens(user), user

    @staticmethod
    def login_user(username, password):
        """Authenticate user and return JWT tokens."""
        user = authenticate(username=username, password=password)
        if user is None:
            return None, None
        return AuthService._get_tokens(user), user

    @staticmethod
    def _get_tokens(user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
