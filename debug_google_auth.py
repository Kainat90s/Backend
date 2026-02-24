import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from integrations.services import GoogleOAuthService

print("Testing Google Auth URL Generation...")
print(f"Client ID: {settings.GOOGLE_CLIENT_ID}")
print(f"Redirect URI: {settings.GOOGLE_REDIRECT_URI}")

try:
    auth_url, state = GoogleOAuthService.get_auth_url()
    print("SUCCESS!")
    print(f"Auth URL: {auth_url}")
except Exception as e:
    print("FAILED!")
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()
