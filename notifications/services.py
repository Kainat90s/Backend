from django.core.mail import send_mail
from django.conf import settings

from .models import NotificationLog


class NotificationService:
    """Business logic for sending notifications."""

    @staticmethod
    def send_booking_confirmation(booking):
        """Send confirmation email to both client and admin."""
        slot = booking.slot

        # Email to client
        client_subject = f'Booking Confirmed — {slot.date} at {slot.start_time}'
        client_body = (
            f'Hello {booking.client_name},\n\n'
            f'Your booking has been confirmed!\n\n'
            f'📅 Date: {slot.date}\n'
            f'⏰ Time: {slot.start_time} – {slot.end_time}\n'
            f'📋 Type: {booking.get_meeting_type_display()}\n'
        )
        if booking.meet_link:
            client_body += f'🔗 Meeting Link: {booking.meet_link}\n'
        client_body += (
            f'\nIf you need to cancel, please contact us.\n\n'
            f'Best regards,\nByteSlot Team'
        )
        NotificationService._send_email(
            booking.client_email, booking.client_name,
            client_subject, client_body,
            NotificationLog.NotificationType.CONFIRMATION, booking.id,
        )

        # Email to admin
        admin_subject = f'New Booking: {booking.client_name} on {slot.date}'
        admin_body = (
            f'You have a new booking:\n\n'
            f'👤 Client: {booking.client_name} ({booking.client_email})\n'
            f'📅 Date: {slot.date}\n'
            f'⏰ Time: {slot.start_time} – {slot.end_time}\n'
            f'📋 Type: {booking.get_meeting_type_display()}\n'
            f'📝 Notes: {booking.notes or "None"}\n'
        )
        if slot.admin.email:
            NotificationService._send_email(
                slot.admin.email, slot.admin.get_full_name(),
                admin_subject, admin_body,
                NotificationLog.NotificationType.CONFIRMATION, booking.id,
            )

    @staticmethod
    def send_booking_cancellation(booking):
        """Send cancellation email to both client and admin."""
        slot = booking.slot

        client_subject = f'Booking Cancelled — {slot.date} at {slot.start_time}'
        client_body = (
            f'Hello {booking.client_name},\n\n'
            f'Your booking on {slot.date} at {slot.start_time} has been cancelled.\n\n'
            f'If this was a mistake, please rebook.\n\n'
            f'Best regards,\nByteSlot Team'
        )
        NotificationService._send_email(
            booking.client_email, booking.client_name,
            client_subject, client_body,
            NotificationLog.NotificationType.CANCELLATION, booking.id,
        )

        # Notify admin
        if slot.admin.email:
            admin_subject = f'Booking Cancelled: {booking.client_name} on {slot.date}'
            admin_body = (
                f'The following booking has been cancelled:\n\n'
                f'👤 Client: {booking.client_name}\n'
                f'📅 Date: {slot.date}\n'
                f'⏰ Time: {slot.start_time} – {slot.end_time}\n'
            )
            NotificationService._send_email(
                slot.admin.email, slot.admin.get_full_name(),
                admin_subject, admin_body,
                NotificationLog.NotificationType.CANCELLATION, booking.id,
            )

    @staticmethod
    def send_meeting_reminder(booking):
        """Send a reminder email 1 hour before the meeting."""
        slot = booking.slot

        subject = f'Reminder: Meeting in 1 hour — {slot.start_time}'
        body = (
            f'Hello {booking.client_name},\n\n'
            f'This is a reminder that your meeting is in 1 hour.\n\n'
            f'📅 Date: {slot.date}\n'
            f'⏰ Time: {slot.start_time} – {slot.end_time}\n'
            f'📋 Type: {booking.get_meeting_type_display()}\n'
        )
        if booking.meet_link:
            body += f'🔗 Meeting Link: {booking.meet_link}\n'
        body += f'\nBest regards,\nByteSlot Team'

        NotificationService._send_email(
            booking.client_email, booking.client_name,
            subject, body,
            NotificationLog.NotificationType.REMINDER, booking.id,
        )

        # Also remind admin
        if slot.admin.email:
            admin_body = (
                f'Reminder: You have a meeting with {booking.client_name} in 1 hour.\n\n'
                f'⏰ Time: {slot.start_time} – {slot.end_time}\n'
            )
            if booking.meet_link:
                admin_body += f'🔗 Meeting Link: {booking.meet_link}\n'
            NotificationService._send_email(
                slot.admin.email, slot.admin.get_full_name(),
                subject, admin_body,
                NotificationLog.NotificationType.REMINDER, booking.id,
            )

    @staticmethod
    def _send_email(to_email, to_name, subject, body, notification_type, booking_id=None):
        """Send email and log it."""
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=True,
            )
            is_sent = True
        except Exception:
            is_sent = False

        NotificationLog.objects.create(
            recipient_email=to_email,
            recipient_name=to_name,
            subject=subject,
            body=body,
            notification_type=notification_type,
            booking_id=booking_id,
            is_sent=is_sent,
        )
