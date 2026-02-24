from datetime import datetime, timedelta
from celery import shared_task
from django.utils import timezone


@shared_task(name='notifications.tasks.send_booking_confirmation_task')
def send_booking_confirmation_task(booking_id):
    """Async task: send booking confirmation emails."""
    from bookings.models import Booking
    from .services import NotificationService

    try:
        booking = Booking.objects.select_related('slot', 'slot__admin').get(pk=booking_id)
        NotificationService.send_booking_confirmation(booking)
    except Booking.DoesNotExist:
        pass


@shared_task(name='notifications.tasks.send_booking_cancellation_task')
def send_booking_cancellation_task(booking_id):
    """Async task: send booking cancellation emails."""
    from bookings.models import Booking
    from .services import NotificationService

    try:
        booking = Booking.objects.select_related('slot', 'slot__admin').get(pk=booking_id)
        NotificationService.send_booking_cancellation(booking)
    except Booking.DoesNotExist:
        pass


@shared_task(name='notifications.tasks.send_upcoming_reminders')
def send_upcoming_reminders():
    """
    Periodic task (Celery Beat): check for meetings starting in ~1 hour
    and send reminder emails. Runs every 15 minutes.
    """
    from bookings.models import Booking
    from .services import NotificationService
    from .models import NotificationLog

    now = timezone.now()
    one_hour_later = now + timedelta(hours=1)

    # Find confirmed bookings starting in the next 45–75 min window
    # to avoid double-sending when beat runs every 15 min
    upcoming = Booking.objects.filter(
        status=Booking.Status.CONFIRMED,
        slot__date=now.date(),
        slot__start_time__gte=(now + timedelta(minutes=45)).time(),
        slot__start_time__lte=(now + timedelta(minutes=75)).time(),
    ).select_related('slot', 'slot__admin')

    for booking in upcoming:
        # Check if reminder already sent
        already_sent = NotificationLog.objects.filter(
            booking_id=booking.id,
            notification_type=NotificationLog.NotificationType.REMINDER,
        ).exists()

        if not already_sent:
            NotificationService.send_meeting_reminder(booking)
