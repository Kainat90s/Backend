from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from .serializers import RegisterSerializer, LoginSerializer, UserSerializer
from .services import AuthService


class RegisterView(generics.CreateAPIView):
    """Register a new user account."""
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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
