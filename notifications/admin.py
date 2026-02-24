from django.contrib import admin
from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'subject', 'notification_type', 'is_sent', 'sent_at')
    list_filter = ('notification_type', 'is_sent', 'sent_at')
    search_fields = ('recipient_email', 'subject')
    ordering = ('-sent_at',)
    readonly_fields = ('recipient_email', 'recipient_name', 'subject', 'body',
                       'notification_type', 'booking_id', 'sent_at', 'is_sent')
