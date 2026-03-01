from celery import shared_task
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

@shared_task(name='integrations.tasks.create_google_meet_link_task')
def create_google_meet_link_task(booking_id):
    """
    Async task to create a Google Meet link for a booking.
    Then triggers the confirmation email.
    """
    from bookings.models import Booking
    from integrations.services import GoogleMeetService
    from notifications.tasks import send_booking_confirmation_task

    try:
        booking = Booking.objects.select_related('slot', 'slot__admin').get(pk=booking_id)
        
        # Only create if it's a video meeting and doesn't have a link yet
        if booking.meeting_type == 'video' and not booking.meet_link:
            meet_link = GoogleMeetService.create_meet_event(
                admin_user=booking.slot.admin,
                summary=f'Meeting with {booking.client_name}',
                start_date=booking.slot.date,
                start_time=booking.slot.start_time,
                end_time=booking.slot.end_time,
                attendee_email=booking.client_email,
            )
            
            if meet_link:
                booking.meet_link = meet_link
                booking.save(update_fields=['meet_link', 'updated_at'])
                logger.info(f"Created Meet link for Booking {booking_id}: {meet_link}")
            else:
                logger.warning(f"Failed to create Meet link for Booking {booking_id}")

        # Always trigger confirmation task after link generation attempt
        send_booking_confirmation_task.delay(booking.id)

    except Booking.DoesNotExist:
        logger.error(f"Booking {booking_id} not found for Meet link creation task")
    except Exception as e:
        logger.exception(f"Error in create_google_meet_link_task for Booking {booking_id}: {str(e)}")
        # Still try to send confirmation even if Meet fails
        send_booking_confirmation_task.delay(booking_id)
