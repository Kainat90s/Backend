import os
import django
import sys

# Setup Django environment
sys.path.append(r'c:\Users\PMLS\OneDrive\Desktop\byteslot\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from availability.models import AvailabilitySlot
from bookings.models import Booking
from django.utils import timezone
from datetime import timedelta

def check_db():
    total_slots = AvailabilitySlot.objects.count()
    total_bookings = Booking.objects.count()
    
    now = timezone.now().date()
    monday = now - timedelta(days=now.weekday())
    sunday = monday + timedelta(days=6)
    
    slots_this_week = AvailabilitySlot.objects.filter(date__range=(monday, sunday)).count()
    future_slots = AvailabilitySlot.objects.filter(date__gt=sunday).count()
    
    print(f"Total Slots: {total_slots}")
    print(f"Total Bookings: {total_bookings}")
    print(f"Slots in current week ({monday} - {sunday}): {slots_this_week}")
    print(f"Slots in future (beyond {sunday}): {future_slots}")
    
    print("\nDate Breakdown:")
    from django.db.models import Count
    date_counts = AvailabilitySlot.objects.filter(date__gte=now).values('date').annotate(count=Count('id')).order_by('date')
    for item in date_counts:
        print(f"{item['date']}: {item['count']} slots")
    
    if total_slots > 0:
        latest = AvailabilitySlot.objects.order_by('-date').first()
        print(f"Latest slot date: {latest.date}")

if __name__ == "__main__":
    check_db()
