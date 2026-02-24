import os
import django
import sys

sys.path.append(r'c:\Users\PMLS\OneDrive\Desktop\byteslot\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from availability.models import AvailabilitySlot
from django.db.models import Count, Q
from django.utils import timezone

def debug():
    today = timezone.now().date()
    stats = AvailabilitySlot.objects.filter(date__gte=today).values('date').annotate(
        total=Count('id'),
        booked=Count('id', filter=Q(is_booked=True)),
        available=Count('id', filter=Q(is_booked=False))
    ).order_by('date')
    
    print(f"{'Date':<15} | {'Total':<10} | {'Booked':<10} | {'Available':<10}")
    print("-" * 50)
    for s in stats:
        print(f"{str(s['date']):<15} | {s['total']:<10} | {s['booked']:<10} | {s['available']:<10}")

if __name__ == "__main__":
    debug()
