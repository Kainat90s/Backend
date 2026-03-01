from django.core.mail import send_mail
from django.conf import settings

from .models import NotificationLog


class NotificationService:
    """Business logic for sending notifications."""

    @staticmethod
    def send_booking_pending(booking):
        """Send pending notification email to both client and admin."""
        slot = booking.slot

        # Email to client
        client_subject = f'Booking Received (Pending) — {slot.date} at {slot.start_time}'
        client_body = (
            f'Hello {booking.client_name},\n\n'
            f'We have received your booking request. It is currently PENDING approval.\n\n'
            f'📅 Date: {slot.date}\n'
            f'⏰ Time: {slot.start_time} – {slot.end_time}\n'
            f'📋 Type: {booking.get_meeting_type_display()}\n'
            f'📝 Purpose: {booking.notes or "Not specified"}\n\n'
            f'You will receive another email once the admin confirms your meeting.\n\n'
            f'Best regards,\nByteSlot Team'
        )
        NotificationService._send_email(
            booking.client_email, booking.client_name,
            client_subject, client_body,
            NotificationLog.NotificationType.CONFIRMATION, booking.id, # Using confirmation log type for now or add PENDING if model allows
        )

        # Email to admin
        admin_subject = f'New Booking Request: {booking.client_name} on {slot.date}'
        admin_body = (
            f'You have a new booking request waiting for approval:\n\n'
            f'👤 Client: {booking.client_name} ({booking.client_email})\n'
            f'📅 Date: {slot.date}\n'
            f'⏰ Time: {slot.start_time} – {slot.end_time}\n'
            f'📋 Type: {booking.get_meeting_type_display()}\n'
            f'📝 Purpose: {booking.notes or "None"}\n\n'
            f'Please log in to the dashboard to confirm or cancel this booking.'
        )
        if slot.admin.email:
            NotificationService._send_email(
                slot.admin.email, slot.admin.get_full_name(),
                admin_subject, admin_body,
                NotificationLog.NotificationType.CONFIRMATION, booking.id,
            )

    @staticmethod
    def send_booking_confirmation(booking):
        """Send confirmation email to both client and admin."""
        slot = booking.slot

        # Email to client
        client_subject = f'Booking Confirmed — {slot.date} at {slot.start_time}'
        client_body = (
            f'Hello {booking.client_name},\n\n'
            f'Your booking has been CONFIRMED!\n\n'
            f'📅 Date: {slot.date}\n'
            f'⏰ Time: {slot.start_time} – {slot.end_time}\n'
            f'📋 Type: {booking.get_meeting_type_display()}\n'
            f'📝 Purpose: {booking.notes or "None"}\n'
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
        admin_subject = f'Meeting Confirmed: {booking.client_name} on {slot.date}'
        admin_body = (
            f'Meeting confirmed with {booking.client_name}:\n\n'
            f'👤 Client: {booking.client_name} ({booking.client_email})\n'
            f'📅 Date: {slot.date}\n'
            f'⏰ Time: {slot.start_time} – {slot.end_time}\n'
            f'📋 Type: {booking.get_meeting_type_display()}\n'
            f'📝 Notes: {booking.notes or "None"}\n'
        )
        if booking.meet_link:
            admin_body += f'🔗 Meeting Link: {booking.meet_link}\n'
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
            f'Your booking on {slot.date} at {slot.start_time} has been CANCELLED.\n\n'
            f'📝 Purpose: {booking.notes or "None"}\n\n'
            f'If this was a mistake, please rebook or contact us.\n\n'
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
                f'📝 Purpose: {booking.notes or "None"}\n'
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
        """Send email and log it using dynamic SMTP settings if available."""
        from django.core.mail import get_connection
        from core.models import SystemSettings
        
        settings_db = SystemSettings.load()
        from_email = settings_db.default_from_email or settings.DEFAULT_FROM_EMAIL
        
        is_sent = False
        try:
            # Use dynamic SMTP if user/pass are provided in DB
            if settings_db.email_host_user and settings_db.email_host_password:
                connection = get_connection(
                    host=settings_db.email_host,
                    port=settings_db.email_port,
                    username=settings_db.email_host_user,
                    password=settings_db.email_host_password,
                    use_tls=settings_db.email_use_tls,
                )
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=from_email,
                    recipient_list=[to_email],
                    fail_silently=False,
                    connection=connection,
                )
            else:
                # Fallback to .env settings
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=from_email,
                    recipient_list=[to_email],
                    fail_silently=False,
                )
            is_sent = True
        except Exception as e:
            # Log error locally for debugging (optional: could add to NotificationLog)
            print(f"SMTP Error: {str(e)}")
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
