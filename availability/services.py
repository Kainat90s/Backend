from datetime import datetime, timedelta, time

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError

from .models import AvailabilitySlot
from core.models import SystemSettings


class AvailabilityService:
    """Business logic for availability slot management."""

    @staticmethod
    def create_slot(admin_user, date, start_time, end_time):
        """Create a single availability slot."""
        slot = AvailabilitySlot(
            admin=admin_user,
            date=date,
            start_time=start_time,
            end_time=end_time,
        )
        try:
            slot.full_clean()
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict)

        slot.save()
        return slot

    @staticmethod
    def create_slots_range(admin_user, date, start_time, end_time, duration_mins=None):
        """
        Create multiple slots by splitting a range into chunks, 
        OR a single large slot if duration_mins is None/0 (Flexible Mode).
        Respects buffer_after_minutes from SystemSettings.
        """
        # --- FLEXIBLE MODE (Single Block) ---
        if not duration_mins:
            return [AvailabilityService.create_slot(admin_user, date, start_time, end_time)]

        # --- NORMAL SPLITTING MODE ---
        settings = SystemSettings.load()
        buffer_after = timedelta(minutes=settings.buffer_after_minutes)

        start_dt = datetime.combine(date, start_time)
        end_dt = datetime.combine(date, end_time)
        duration = timedelta(minutes=duration_mins)

        created_slots = []
        current_start = start_dt

        while current_start + duration <= end_dt:
            current_end = current_start + duration
            
            try:
                slot = AvailabilityService.create_slot(
                    admin_user, 
                    date, 
                    current_start.time(), 
                    current_end.time()
                )
                created_slots.append(slot)
            except ValidationError:
                # If one slot overlaps, we skip it but continue with others
                pass
            
            # Step forward by duration + buffer
            current_start = current_end + buffer_after

        if not created_slots:
            raise ValidationError({'detail': 'No slots could be created in this range (possibly due to duration or overlaps).'})
            
        return created_slots

    @staticmethod
    def get_available_slots(from_date=None, to_date=None):
        """Return unbooked future availability slots."""
        from django.utils import timezone

        qs = AvailabilitySlot.objects.filter(is_booked=False)

        if from_date:
            qs = qs.filter(date__gte=from_date)
        else:
            qs = qs.filter(date__gte=timezone.now().date())

        if to_date:
            qs = qs.filter(date__lte=to_date)

        return qs.order_by('date', 'start_time')

    @staticmethod
    def delete_day_slots(admin_user, date):
        """
        Delete all slots for a given date. Cancel any active bookings first.
        Returns dict with deleted_slots and cancelled_bookings counts.
        """
        from django.db import transaction
        from bookings.models import Booking
        from bookings.services import BookingService

        slots = AvailabilitySlot.objects.filter(admin=admin_user, date=date)

        if not slots.exists():
            raise ValidationError({'date': f'No slots found for {date}.'})

        cancelled_count = 0

        with transaction.atomic():
            # Cancel all active bookings on these slots
            active_bookings = Booking.objects.filter(
                slot__in=slots,
                status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
            )

            for booking in active_bookings:
                BookingService.cancel_booking(booking_id=booking.id)
                cancelled_count += 1

            # Now delete all slots for this date
            deleted_count = slots.count()
            slots.delete()

        return {
            'deleted_slots': deleted_count,
            'cancelled_bookings': cancelled_count,
        }

    @staticmethod
    def check_buffer_compliance(slot):
        """
        Check that the slot respects buffer_before and buffer_after
        settings with adjacent bookings.
        Returns True if compliant, raises ValidationError otherwise.
        """
        settings = SystemSettings.load()
        buffer_before = timedelta(minutes=settings.buffer_before_minutes)
        buffer_after = timedelta(minutes=settings.buffer_after_minutes)

        slot_start = datetime.combine(slot.date, slot.start_time)
        slot_end = datetime.combine(slot.date, slot.end_time)

        # Check for bookings that end too close before this slot starts
        from bookings.models import Booking

        preceding_bookings = Booking.objects.filter(
            slot__date=slot.date,
            slot__end_time__gt=(slot_start - buffer_before).time(),
            slot__end_time__lte=slot.start_time,
            status=Booking.Status.CONFIRMED,
        ).exclude(slot=slot)

        if buffer_before.total_seconds() > 0 and preceding_bookings.exists():
            for booking in preceding_bookings:
                booking_end = datetime.combine(slot.date, booking.slot.end_time)
                required_start = booking_end + buffer_after  # buffer after previous
                if slot_start < required_start:
                    raise ValidationError({
                        'start_time': f'Buffer violation: previous meeting ends at {booking.slot.end_time}, '
                                      f'next booking cannot start before {required_start.time()} '
                                      f'(buffer_after={settings.buffer_after_minutes} min).'
                    })

        # Check for bookings that start too close after this slot ends
        following_bookings = Booking.objects.filter(
            slot__date=slot.date,
            slot__start_time__gte=slot.end_time,
            slot__start_time__lt=(slot_end + buffer_after).time(),
            status=Booking.Status.CONFIRMED,
        ).exclude(slot=slot)

        if buffer_after.total_seconds() > 0 and following_bookings.exists():
            for booking in following_bookings:
                booking_start = datetime.combine(slot.date, booking.slot.start_time)
                required_gap = slot_end + buffer_after
                if booking_start < required_gap:
                    raise ValidationError({
                        'end_time': f'Buffer violation: next meeting starts at {booking.slot.start_time}, '
                                    f'requires at least {settings.buffer_after_minutes} min buffer after.'
                    })

        return True
