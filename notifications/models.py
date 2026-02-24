from django.db import models


class NotificationLog(models.Model):
    """Log of all notifications sent by the system."""

    class NotificationType(models.TextChoices):
        CONFIRMATION = 'confirmation', 'Booking Confirmation'
        CANCELLATION = 'cancellation', 'Booking Cancellation'
        REMINDER = 'reminder', 'Meeting Reminder'

    recipient_email = models.EmailField()
    recipient_name = models.CharField(max_length=150, blank=True, default='')
    subject = models.CharField(max_length=255)
    body = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
    )
    booking_id = models.IntegerField(null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(default=False)

    class Meta:
        db_table = 'notifications_log'
        ordering = ['-sent_at']
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'

    def __str__(self):
        return f'{self.notification_type} → {self.recipient_email} ({self.sent_at})'
