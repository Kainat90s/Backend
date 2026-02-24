from rest_framework import serializers
from .models import GoogleOAuthCredential


class GoogleOAuthStatusSerializer(serializers.Serializer):
    is_connected = serializers.BooleanField()
    connected_at = serializers.DateTimeField(required=False, allow_null=True)
