from django.contrib import admin
from .models import GoogleOAuthCredential


@admin.register(GoogleOAuthCredential)
class GoogleOAuthCredentialAdmin(admin.ModelAdmin):
    list_display = ('user', 'token_expiry', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('access_token', 'refresh_token', 'token_expiry',
                       'scopes', 'created_at', 'updated_at')
