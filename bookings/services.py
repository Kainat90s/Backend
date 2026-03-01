from datetime import datetime, timedelta

from django.db import transaction
from rest_framework.exceptions import ValidationError, PermissionDenied

from .models import Booking
from availability.models import AvailabilitySlot
from availability.services import AvailabilityService
from core.models import SystemSettings


class BookingService:
    """
    Business logic for booking creation and management.
    Implements the full validation pipeline:
      1) Slot exists
      2) Slot not already booked
      3) Slot not on weekend
      4) Buffer rules
      5) No overlapping bookings
      6) Create booking + mark slot booked + trigger integrations
    """

    @staticmethod
    @transaction.atomic
    def create_booking(slot_id, client_name, client_email, meeting_type,
                       notes='', client_user=None, custom_start=None, custom_end=None):
        """Create a booking with full validation and optional slot splitting."""

        # 1) Check slot exists
        try:
            slot = AvailabilitySlot.objects.select_for_update().get(pk=slot_id)
        except AvailabilitySlot.DoesNotExist:
            raise ValidationError(
                {'slot': 'The requested time slot does not exist.'},
                code='invalid_slot',
            )

        # 2) Check slot not already booked
        if slot.is_booked:
            raise ValidationError(
                {'slot': 'This time slot has already been reserved.'},
                code='slot_reserved',
            )

        # 3) Check slot not on weekend
        if slot.day_of_week in (5, 6):
            raise ValidationError(
                {'slot': 'Bookings are not allowed on weekends.'},
                code='weekend_not_allowed',
            )

        # --- DYNAMIC SPLITTING LOGIC ---
        if custom_start and custom_end:
            # Validate custom times are within slot
            if custom_start < slot.start_time or custom_end > slot.end_time:
                raise ValidationError({'detail': f'Requested time must be within {slot.start_time.strftime("%H:%M")} - {slot.end_time.strftime("%H:%M")}'})
            if custom_start >= custom_end:
                raise ValidationError({'detail': 'End time must be after start time'})

            original_start = slot.start_time
            original_end = slot.end_time

            # 1. Update current slot to be exactly the booked window FIRST
            # This "frees up" the leftover time in the DB for the next create calls
            slot.start_time = custom_start
            slot.end_time = custom_end
            slot.save(update_fields=['start_time', 'end_time'])

            # 2. Create leftover slot before (if any)
            if custom_start > original_start:
                AvailabilitySlot.objects.create(
                    admin=slot.admin,
                    date=slot.date,
                    start_time=original_start,
                    end_time=custom_start,
                    is_booked=False
                )

            # 3. Create leftover slot after (if any)
            if custom_end < original_end:
                AvailabilitySlot.objects.create(
                    admin=slot.admin,
                    date=slot.date,
                    start_time=custom_end,
                    end_time=original_end,
                    is_booked=False
                )

        # 4) Check buffer rules
        AvailabilityService.check_buffer_compliance(slot)

        # 5) Check overlapping bookings on the same day (strict check)
        overlapping = Booking.objects.filter(
            slot__date=slot.date,
            slot__start_time__lt=slot.end_time,
            slot__end_time__gt=slot.start_time,
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
        )
        if overlapping.exists():
            raise ValidationError(
                {'slot': 'This time slot conflicts with an existing booking.'},
                code='slot_conflict',
            )

        # 6) All checks passed — create booking
        booking = Booking.objects.create(
            slot=slot,
            client=client_user,
            client_name=client_name,
            client_email=client_email,
            meeting_type=meeting_type,
            notes=notes,
            status=Booking.Status.PENDING,
        )

        # Mark slot as booked
        slot.is_booked = True
        slot.save(update_fields=['is_booked'])

        # Trigger background tasks
        # First, notify both that a request has been received (PENDING)
        from notifications.tasks import send_booking_pending_task
        transaction.on_commit(lambda: send_booking_pending_task.delay(booking.id))

        # Note: We NO LONGER trigger create_google_meet_link_task here 
        # because that should happen when the admin CONFIRMS the booking,
        # otherwise we'd create Meet links for meetings that might get cancelled.

        return booking

    @staticmethod
    def approve_booking(booking_id, user=None):
        """Approve a pending booking."""
        return BookingService.update_booking_status(booking_id, Booking.Status.CONFIRMED, user)

    @staticmethod
    def update_booking_status(booking_id, status, user=None):
        """Update a booking's status with necessary side effects."""
        try:
            booking = Booking.objects.select_related('slot').get(pk=booking_id)
        except Booking.DoesNotExist:
            raise ValidationError({'booking': 'Booking not found.'})

        if booking.status == status:
            return booking

        old_status = booking.status

        with transaction.atomic():
            # If changing FROM cancelled to something else, check if slot is still free
            if old_status == Booking.Status.CANCELLED and status != Booking.Status.CANCELLED:
                if booking.slot.is_booked:
                    raise ValidationError({'slot': 'The slot for this booking is already taken.'})
                booking.slot.is_booked = True
                booking.slot.save(update_fields=['is_booked'])

            # If changing TO cancelled, free the slot
            elif status == Booking.Status.CANCELLED and old_status != Booking.Status.CANCELLED:
                booking.slot.is_booked = False
                booking.slot.save(update_fields=['is_booked'])

            booking.status = status
            booking.save(update_fields=['status', 'updated_at'])

            if status == Booking.Status.CONFIRMED:
                # For video meetings, use background task to generate link and notify
                if booking.meeting_type == Booking.MeetingType.VIDEO and not booking.meet_link:
                    from integrations.tasks import create_google_meet_link_task
                    transaction.on_commit(lambda: create_google_meet_link_task.delay(booking.id))
                else:
                    # Notify immediately if not video or link already exists
                    transaction.on_commit(lambda: BookingService._send_confirmation(booking))

            # Side effect: Cancelled
            if status == Booking.Status.CANCELLED:
                transaction.on_commit(lambda: BookingService._send_cancellation(booking))

        return booking

    @staticmethod
    def cancel_booking(booking_id, user=None):
        """Cancel a booking and free the slot."""
        return BookingService.update_booking_status(booking_id, Booking.Status.CANCELLED, user)

    @staticmethod
    def _try_create_meet_link(booking, slot):
        """DEPRECATED: Now handled via create_google_meet_link_task in integrations.tasks"""
        pass

    @staticmethod
    def _send_pending(booking):
        """Trigger async pending notification."""
        try:
            from notifications.tasks import send_booking_pending_task
            send_booking_pending_task.delay(booking.id)
        except Exception:
            pass

    @staticmethod
    def _send_confirmation(booking):
        """Trigger async confirmation notification."""
        try:
            from notifications.tasks import send_booking_confirmation_task
            send_booking_confirmation_task.delay(booking.id)
        except Exception:
            pass  # Notifications are best-effort

    @staticmethod
    def _send_cancellation(booking):
        """Trigger async cancellation notification."""
        try:
            from notifications.tasks import send_booking_cancellation_task
            send_booking_cancellation_task.delay(booking.id)
        except Exception:
            pass  # Notifications are best-effort
