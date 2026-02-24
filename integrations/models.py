from django.conf import settings
from django.db import models


class GoogleOAuthCredential(models.Model):
    """Stores Google OAuth tokens for admin users."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='google_credentials',
    )
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_expiry = models.DateTimeField(null=True, blank=True)
    scopes = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'integrations_google_oauth'
        verbose_name = 'Google OAuth Credential'
        verbose_name_plural = 'Google OAuth Credentials'

    def __str__(self):
        return f'Google OAuth for {self.user.username}'
