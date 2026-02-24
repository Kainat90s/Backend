import os
import django
from unittest.mock import patch, MagicMock

# Set up Django environment
print("Setting up Django...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
print("Django setup complete.")

from bookings.services import BookingService
from bookings.models import Booking
from availability.models import AvailabilitySlot
from django.contrib.auth import get_user_model

User = get_user_model()

def test_booking_triggers_task():
    print("Starting verification test logic...")
    
    # 1. Setup mock data
    print("Fetching admin user...")
    admin = User.objects.filter(role='admin').first()
    if not admin:
        print("No admin found, creating test admin...")
        admin = User.objects.create(username='testadmin', role='admin', email='admin@test.com')
        print(f"Created temporary admin user: {admin.username}")

    from datetime import date, time
    print("Creating test availability slot...")
    slot = AvailabilitySlot.objects.create(
        admin=admin,
        date=date(2026, 3, 2),
        start_time=time(10, 0, 0),
        end_time=time(11, 0, 0),
        is_booked=False
    )
    print(f"Created test slot: {slot.id}")

    # 2. Mock the Celery task and service
    print("Patching Celery task and buffer check...")
    with patch('integrations.tasks.create_google_meet_link_task.delay') as mock_task:
        with patch('availability.services.AvailabilityService.check_buffer_compliance', return_value=True):
            print("Calling BookingService.create_booking (this triggers the task)...")
            try:
                booking = BookingService.create_booking(
                    slot_id=slot.id,
                    client_name="Test Client",
                    client_email="client@test.com",
                    meeting_type='VIDEO',
                )
                print("Booking created successfully.")
            except Exception as e:
                print(f"Error during create_booking: {str(e)}")
                raise e
            
            # 3. Verify
            print("Verifying task call...")
            if mock_task.called:
                print("SUCCESS: create_google_meet_link_task.delay was called!")
                print(f"Task called with booking_id: {mock_task.call_args[0][0]}")
            else:
                print("FAILURE: create_google_meet_link_task.delay was NOT called.")

    # Cleanup
    print("Cleaning up test data...")
    if 'booking' in locals():
        booking.delete()
        print("Deleted test booking.")
    slot.delete()
    print("Deleted test slot.")
    print("Test cleanup complete.")

if __name__ == "__main__":
    try:
        test_booking_triggers_task()
    except Exception as e:
        print(f"Error during test: {str(e)}")
