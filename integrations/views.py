from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth import get_user_model
from django.core import signing
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
            redirect_uri = settings.GOOGLE_REDIRECT_URI or request.build_absolute_uri(reverse('google-oauth-callback'))
            signed_state = signing.dumps({'user_id': request.user.id, 'redirect_uri': redirect_uri})
            auth_url, _ = GoogleOAuthService.get_auth_url(
                state=signed_state,
                scopes=GoogleOAuthService.CALENDAR_SCOPES,
                include_granted_scopes=True,
                redirect_uri=redirect_uri,
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
            redirect_uri = settings.GOOGLE_REDIRECT_URI or request.build_absolute_uri(reverse('google-oauth-callback'))
            signed_state = signing.dumps({'flow': 'login', 'redirect_uri': redirect_uri})
            auth_url, _ = GoogleOAuthService.get_auth_url(
                state=signed_state,
                scopes=GoogleOAuthService.LOGIN_SCOPES,
                include_granted_scopes=False,
                redirect_uri=redirect_uri,
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
        error = request.query_params.get('error')
        
        if error:
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
            return redirect(f"{frontend_url}/login?google_error={error}")

        print(f"DEBUG: Google Callback - Code: {(code or '')[:10]}..., State: {(state or '')[:10]}...")

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
            redirect_uri = state_data.get('redirect_uri') or settings.GOOGLE_REDIRECT_URI

            if state_data.get('flow') == 'login':
                print("DEBUG: Login flow detected.")
                credentials = GoogleOAuthService.exchange_code(
                    code,
                    scopes=GoogleOAuthService.LOGIN_SCOPES,
                    redirect_uri=redirect_uri,
                )
                user_info = GoogleOAuthService.get_user_info(credentials)

                email = user_info.get('email')
                if not email:
                    return Response({'error': 'Google did not return an email.'}, status=400)

                user = User.objects.filter(email__iexact=email).first()
                if not user:
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        first_name=user_info.get('given_name', '') or '',
                        last_name=user_info.get('family_name', '') or '',
                        password=User.objects.make_random_password(),
                    )

                # Do not overwrite calendar OAuth credentials with login-only scopes
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
                print(f"DEBUG: User found: {user.email}")
            except User.DoesNotExist:
                print(f"DEBUG: User with ID {user_id} not found.")
                return Response({'error': f'User with ID {user_id} no longer exists.'}, status=404)

            print("DEBUG: Fetching token from Google...")
            GoogleOAuthService.handle_callback(
                code,
                user,
                scopes=GoogleOAuthService.CALENDAR_SCOPES,
                redirect_uri=redirect_uri,
            )
            print("DEBUG: Token saved successfully. Redirecting...")

            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
            return redirect(f"{frontend_url}/settings?google=connected")
        except Exception as e:
            import traceback
            print(f"DEBUG: Callback Exception: {str(e)}")
            print(traceback.format_exc())
            if 'invalid_grant' in str(e):
                frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
                return redirect(f"{frontend_url}/settings?google=invalid_grant")
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
                'owner_email': request.user.email,
            })
        except GoogleOAuthCredential.DoesNotExist:
            # Fallback: if duplicate accounts share the same email, reuse that credential
            if request.user.email:
                cred = GoogleOAuthCredential.objects.filter(user__email__iexact=request.user.email).first()
                if cred:
                    if cred.user_id != request.user.id:
                        cred.user = request.user
                        cred.save(update_fields=['user', 'updated_at'])
                    return Response({
                        'is_connected': True,
                        'connected_at': cred.created_at,
                        'owner_email': cred.user.email,
                    })

            # Final fallback: if exactly one calendar credential exists, treat as connected
            calendar_creds = [
                c for c in GoogleOAuthCredential.objects.all()
                if 'https://www.googleapis.com/auth/calendar.events' in (c.scopes or [])
            ]
            if len(calendar_creds) == 1:
                cred = calendar_creds[0]
                return Response({
                    'is_connected': True,
                    'connected_at': cred.created_at,
                    'owner_email': cred.user.email,
                })

            return Response({
                'is_connected': False,
                'connected_at': None,
                'owner_email': None,
            })


class GoogleOAuthDisconnectView(APIView):
    """Disconnect Google OAuth for the current user."""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        GoogleOAuthCredential.objects.filter(user=request.user).delete()
        return Response({'detail': 'Google account disconnected.'})


class GoogleOAuthHealthView(APIView):
    """Quick health check for Google OAuth configuration."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '') or ''
        client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '') or ''
        redirect_uri = getattr(settings, 'GOOGLE_REDIRECT_URI', '') or ''
        frontend_url = getattr(settings, 'FRONTEND_URL', '') or ''

        configured = bool(client_id and client_secret and redirect_uri)

        return Response({
            'configured': configured,
            'client_id_present': bool(client_id),
            'client_secret_present': bool(client_secret),
            'redirect_uri': redirect_uri,
            'frontend_url': frontend_url,
        })

