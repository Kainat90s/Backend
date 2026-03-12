from django.contrib import admin
from .models import GoogleOAuthCredential


@admin.register(GoogleOAuthCredential)
class GoogleOAuthCredentialAdmin(admin.ModelAdmin):
    list_display = ('user', 'token_expiry', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('access_token', 'refresh_token', 'token_expiry',
                       'scopes', 'created_at', 'updated_at')
