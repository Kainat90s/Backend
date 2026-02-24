from django.shortcuts import redirect
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import GoogleOAuthCredential
from .services import GoogleOAuthService


class GoogleOAuthInitView(APIView):
    """Initiate Google OAuth 2.0 flow — returns the consent URL."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if not getattr(settings, 'GOOGLE_CLIENT_ID', None) or not getattr(settings, 'GOOGLE_CLIENT_SECRET', None):
            return Response(
                {'error': 'Google OAuth credentials are not configured in backend/.env file.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            auth_url, state = GoogleOAuthService.get_auth_url()
            # Store state in session for CSRF validation
            request.session['google_oauth_state'] = state
            return Response({'auth_url': auth_url, 'state': state})
        except Exception as e:
            import traceback
            print(f"DEBUG: Google OAuth Init Error: {str(e)}")
            print(traceback.format_exc())
            return Response(
                {'error': f'Failed to generate Google Auth URL: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GoogleOAuthCallbackView(APIView):
    """Handle Google OAuth 2.0 callback with authorization code."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        code = request.query_params.get('code')
        if not code:
            return Response(
                {'error': 'Authorization code not provided.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            GoogleOAuthService.handle_callback(code, request.user)
            # Redirect to frontend settings page
            return redirect('http://localhost:5173/settings?google=connected')
        except Exception as e:
            return Response(
                {'error': f'OAuth failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )


class GoogleOAuthStatusView(APIView):
    """Check if the current user has connected Google."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            cred = GoogleOAuthCredential.objects.get(user=request.user)
            return Response({
                'is_connected': True,
                'connected_at': cred.created_at,
            })
        except GoogleOAuthCredential.DoesNotExist:
            return Response({
                'is_connected': False,
                'connected_at': None,
            })


class GoogleOAuthDisconnectView(APIView):
    """Disconnect Google OAuth for the current user."""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        GoogleOAuthCredential.objects.filter(user=request.user).delete()
        return Response({'detail': 'Google account disconnected.'})
