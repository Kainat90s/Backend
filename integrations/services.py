import json
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from .models import GoogleOAuthCredential

SCOPES = ['https://www.googleapis.com/auth/calendar.events']


class GoogleOAuthService:
    """Handles Google OAuth 2.0 consent flow."""

    @staticmethod
    def get_auth_url():
        """Generate the Google OAuth consent URL."""
        flow = Flow.from_client_config(
            {
                'web': {
                    'client_id': settings.GOOGLE_CLIENT_ID,
                    'client_secret': settings.GOOGLE_CLIENT_SECRET,
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                    'redirect_uris': [settings.GOOGLE_REDIRECT_URI],
                }
            },
            scopes=SCOPES,
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
        )
        return auth_url, state

    @staticmethod
    def handle_callback(code, user):
        """Exchange authorization code for tokens and save them."""
        flow = Flow.from_client_config(
            {
                'web': {
                    'client_id': settings.GOOGLE_CLIENT_ID,
                    'client_secret': settings.GOOGLE_CLIENT_SECRET,
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                    'redirect_uris': [settings.GOOGLE_REDIRECT_URI],
                }
            },
            scopes=SCOPES,
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        flow.fetch_token(code=code)

        credentials = flow.credentials

        GoogleOAuthCredential.objects.update_or_create(
            user=user,
            defaults={
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token or '',
                'token_expiry': credentials.expiry,
                'scopes': list(credentials.scopes or []),
            },
        )
        return True


class GoogleMeetService:
    """Creates Google Calendar events with Meet conferencing."""

    @staticmethod
    def _get_credentials(admin_user):
        """Load and refresh Google credentials for an admin user."""
        try:
            cred_obj = GoogleOAuthCredential.objects.get(user=admin_user)
        except GoogleOAuthCredential.DoesNotExist:
            return None

        creds = Credentials(
            token=cred_obj.access_token,
            refresh_token=cred_obj.refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=cred_obj.scopes,
        )

        # Auto-refresh if expired
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())

            # Save refreshed token
            cred_obj.access_token = creds.token
            cred_obj.token_expiry = creds.expiry
            cred_obj.save(update_fields=['access_token', 'token_expiry', 'updated_at'])

        return creds

    @staticmethod
    def create_meet_event(admin_user, summary, start_date, start_time, end_time, attendee_email=None):
        """
        Create a Google Calendar event with Google Meet conference.
        Returns the hangout link or None.
        """
        creds = GoogleMeetService._get_credentials(admin_user)
        if not creds:
            return None

        service = build('calendar', 'v3', credentials=creds)

        start_dt = datetime.combine(start_date, start_time)
        end_dt = datetime.combine(start_date, end_time)

        event = {
            'summary': summary,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': settings.TIME_ZONE,
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': settings.TIME_ZONE,
            },
            'conferenceData': {
                'createRequest': {
                    'requestId': f'byteslot-{start_date}-{start_time}',
                    'conferenceSolutionKey': {
                        'type': 'hangoutsMeet',
                    },
                },
            },
        }

        if attendee_email:
            event['attendees'] = [{'email': attendee_email}]

        created_event = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1,
        ).execute()

        # Extract hangoutLink
        return created_event.get('hangoutLink', '')
