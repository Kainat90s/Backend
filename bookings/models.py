from django.conf import settings
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache


class Booking(models.Model):
    """A confirmed or pending booking against an availability slot."""

    class MeetingType(models.TextChoices):
        IN_PERSON = 'in_person', 'In Person'
        VIDEO = 'video', 'Video Call'
        PHONE = 'phone', 'Phone Call'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'

    slot = models.ForeignKey(
        'availability.AvailabilitySlot',
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings',
    )
    client_name = models.CharField(max_length=150)
    client_email = models.EmailField()
    meeting_type = models.CharField(
        max_length=20,
        choices=MeetingType.choices,
        default=MeetingType.VIDEO,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    meet_link = models.URLField(blank=True, default='')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bookings_booking'
        ordering = ['-created_at']
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['client', 'status']),
        ]

    def __str__(self):
        return f'Booking #{self.pk} — {self.client_name} on {self.slot.date} ({self.status})'

@receiver([post_save, post_delete], sender=Booking)
def clear_booking_cache(sender, **kwargs):
    cache.clear()
