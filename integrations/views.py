from django.conf import settings
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth import get_user_model
from django.core import signing
from django.utils.text import slugify
from accounts.services import AuthService
from .models import GoogleOAuthCredential
from .services import GoogleOAuthService

User = get_user_model()


class GoogleOAuthInitView(APIView):
    """Initiate Google OAuth 2.0 flow - returns the consent URL."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if not getattr(settings, 'GOOGLE_CLIENT_ID', None) or not getattr(settings, 'GOOGLE_CLIENT_SECRET', None):
            return Response(
                {'error': 'Google OAuth credentials are not configured in backend/.env file.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Sign the user ID to recover it in the callback
            signed_state = signing.dumps({'user_id': request.user.id})
            auth_url, _ = GoogleOAuthService.get_auth_url(
                state=signed_state,
                scopes=GoogleOAuthService.CALENDAR_SCOPES,
                include_granted_scopes=True,
            )
            return Response({'auth_url': auth_url, 'state': signed_state})
        except Exception as e:
            import traceback
            print(f"DEBUG: Google OAuth Init Error: {str(e)}")
            print(traceback.format_exc())
            return Response(
                {'error': f'Failed to generate Google Auth URL: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GoogleOAuthLoginInitView(APIView):
    """Public login via Google OAuth - returns the consent URL."""
    permission_classes = (AllowAny,)

    def get(self, request):
        if not getattr(settings, 'GOOGLE_CLIENT_ID', None) or not getattr(settings, 'GOOGLE_CLIENT_SECRET', None):
            return Response(
                {'error': 'Google OAuth credentials are not configured in backend/.env file.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            signed_state = signing.dumps({'flow': 'login'})
            auth_url, _ = GoogleOAuthService.get_auth_url(
                state=signed_state,
                scopes=GoogleOAuthService.LOGIN_SCOPES,
                include_granted_scopes=False,
            )
            return Response({'auth_url': auth_url, 'state': signed_state})
        except Exception as e:
            import traceback
            print(f"DEBUG: Google OAuth Login Init Error: {str(e)}")
            print(traceback.format_exc())
            return Response(
                {'error': f'Failed to generate Google Auth URL: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GoogleOAuthCallbackView(APIView):
    """Handle Google OAuth 2.0 callback with authorization code."""
    permission_classes = (AllowAny,) # Google redirects don't have Auth headers

    def get(self, request):
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        
        print(f"DEBUG: Google Callback - Code: {code[:10]}..., State: {state[:10]}...")

        if not code or not state:
            return Response(
                {'error': 'Authorization code or state not provided by Google.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Recover the user and original state from signed state parameter
            try:
                state_data = signing.loads(state, max_age=3600)
            except Exception as sign_err:
                print(f"DEBUG: Signature verification failed: {str(sign_err)}")
                return Response({'error': f'Invalid or expired state: {str(sign_err)}'}, status=400)

            # Public login flow
            if state_data.get('flow') == 'login':
                print("DEBUG: Login flow detected.")
                credentials = GoogleOAuthService.exchange_code(
                    code,
                    scopes=GoogleOAuthService.LOGIN_SCOPES,
                )
                user_info = GoogleOAuthService.get_user_info(credentials)

                email = user_info.get('email')
                if not email:
                    return Response({'error': 'Google did not return an email.'}, status=400)

                user = User.objects.filter(email__iexact=email).first()
                if not user:
                    base_username = slugify((email.split('@')[0] if email else '') or user_info.get('id', 'user'))
                    if not base_username:
                        base_username = f"user{user_info.get('id', '')}" or 'user'
                    candidate = base_username
                    suffix = 1
                    while User.objects.filter(username=candidate).exists():
                        suffix += 1
                        candidate = f"{base_username}{suffix}"

                    user = User.objects.create_user(
                        username=candidate,
                        email=email,
                        first_name=user_info.get('given_name', '') or '',
                        last_name=user_info.get('family_name', '') or '',
                        password=User.objects.make_random_password(),
                    )

                GoogleOAuthService.save_credentials(credentials, user)
                tokens = AuthService._get_tokens(user)
                frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
                redirect_url = f"{frontend_url}/login#access={tokens['access']}&refresh={tokens['refresh']}"
                return redirect(redirect_url)

            user_id = state_data.get('user_id')
            print(f"DEBUG: Signature valid. Recovered User ID: {user_id}")
            if not user_id:
                return Response({'error': 'User ID missing in state.'}, status=400)

            try:
                user = User.objects.get(id=user_id)
                print(f"DEBUG: User found: {user.username}")
            except User.DoesNotExist:
                print(f"DEBUG: User with ID {user_id} not found.")
                return Response({'error': f'User with ID {user_id} no longer exists.'}, status=404)

            print("DEBUG: Fetching token from Google...")
            GoogleOAuthService.handle_callback(
                code,
                user,
                scopes=GoogleOAuthService.CALENDAR_SCOPES,
            )
            print("DEBUG: Token saved successfully. Redirecting...")

            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
            return redirect(f"{frontend_url}/settings?google=connected")
        except Exception as e:
            import traceback
            print(f"DEBUG: Callback Exception: {str(e)}")
            print(traceback.format_exc())
            return Response(
                {'error': f'OAuth Process Failed: {str(e)}'},
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

