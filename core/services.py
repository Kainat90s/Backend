from datetime import date, timedelta, datetime, time
from django.db.models import Sum, Q, F
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import SystemSettings


class DashboardService:
    """Business logic for the admin dashboard."""

    @staticmethod
    def get_current_week_range():
        """Return (monday, friday) of the current week."""
        today = date.today()
        monday = today - timedelta(days=today.weekday())     # Monday = 0
        friday = monday + timedelta(days=4)                  # Friday = 4
        sunday = monday + timedelta(days=6)                  # Sunday = 6
        return monday, friday, sunday

    @staticmethod
    def get_weekly_available_hours():
        """
        Calculate total available hours for the next 7 days starting from today.
        Optimized: Uses a single query with aggregation.
        """
        from availability.models import AvailabilitySlot
        from django.db.models import Sum, DurationField, ExpressionWrapper, F
        
        today = date.today()
        next_week = today + timedelta(days=6)
        
        # Aggregate daily minutes in one query
        daily_stats = AvailabilitySlot.objects.filter(
            date__range=(today, next_week),
            is_booked=False
        ).annotate(
            duration=ExpressionWrapper(
                F('end_time') - F('start_time'),
                output_field=DurationField()
            )
        ).values('date').annotate(
            total_minutes=Sum('duration')
        ).order_by()
        
        stats_map = {item['date']: item['total_minutes'].total_seconds() / 60 for item in daily_stats if item['total_minutes']}
        
        result = []
        for i in range(7):
            current_date = today + timedelta(days=i)
            day_name = current_date.strftime('%A')
            total_minutes = stats_map.get(current_date, 0)
            
            result.append({
                'day': day_name,
                'date': current_date,
                'hours': round(total_minutes / 60, 1),
                'is_off': current_date.weekday() >= 5,
            })

        return result

    @staticmethod
    def get_upcoming_meetings(limit=5):
        """Return the next N confirmed bookings."""
        from bookings.models import Booking

        now = timezone.now()
        bookings = Booking.objects.filter(
            status=Booking.Status.CONFIRMED,
            slot__date__gte=now.date(),
        ).select_related('slot').order_by('slot__date', 'slot__start_time')[:limit]

        return [
            {
                'id': b.id,
                'client_name': b.client_name,
                'date': b.slot.date,
                'time': b.slot.start_time,
                'meeting_type': b.get_meeting_type_display(),
                'status': b.get_status_display(),
            }
            for b in bookings
        ]

    @staticmethod
    def get_weekly_stats():
        """
        Return booking statistics for all upcoming events.
        """
        from bookings.models import Booking
        from availability.models import AvailabilitySlot
        from django.db.models import Count, Q

        today = date.today()

        # Conditionally aggregate all upcoming booking stats
        booking_stats = Booking.objects.filter(
            slot__date__gte=today
        ).aggregate(
            total=Count('id'),
            confirmed=Count('id', filter=Q(status=Booking.Status.CONFIRMED)),
            cancelled=Count('id', filter=Q(status=Booking.Status.CANCELLED))
        )

        available_count = AvailabilitySlot.objects.filter(
            date__gte=today,
            is_booked=False
        ).count()

        return {
            'total_bookings_this_week': booking_stats['total'], # Keep old key for frontend compatibility
            'available_slots_remaining': available_count,
            'confirmed_bookings': booking_stats['confirmed'],
            'cancelled_bookings': booking_stats['cancelled'],
        }
