from rest_framework import serializers
from .models import NotificationLog


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = ('id', 'recipient_email', 'recipient_name', 'subject',
                  'notification_type', 'booking_id', 'sent_at', 'is_sent')
