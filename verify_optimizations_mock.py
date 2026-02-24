import os
import django
from unittest.mock import patch, MagicMock

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from bookings.services import BookingService
from bookings.models import Booking
from availability.models import AvailabilitySlot
from django.contrib.auth import get_user_model

User = get_user_model()

def test_booking_logic_simple():
    print("Starting simplified verification test...")
    
    # Mock AvailabilitySlot and Booking objects instead of creating them in DB
    # to avoid MS SQL locking issues during quick successive calls
    
    mock_admin = MagicMock(spec=User)
    mock_admin.role = 'admin'
    
    mock_slot = MagicMock(spec=AvailabilitySlot)
    mock_slot.id = 999
    mock_slot.admin = mock_admin
    mock_slot.is_booked = False
    mock_slot.day_of_week = 0 # Monday
    
    # Create a mock for Booking.objects.create and other DB calls
    with patch('availability.models.AvailabilitySlot.objects.select_for_update') as mock_sfu:
        mock_sfu.return_value.get.return_value = mock_slot
        
        with patch('bookings.models.Booking.objects.create') as mock_booking_create:
            mock_booking = MagicMock(spec=Booking)
            mock_booking.id = 888
            mock_booking_create.return_value = mock_booking
            
            with patch('bookings.models.Booking.objects.filter') as mock_booking_filter:
                mock_booking_filter.return_value.exists.return_value = False
                
                with patch('availability.services.AvailabilityService.check_buffer_compliance', return_value=True):
                    with patch('integrations.tasks.create_google_meet_link_task.delay') as mock_task:
                        
                        print("Calling BookingService.create_booking with mocked DB...")
                        BookingService.create_booking(
                            slot_id=999,
                            client_name="Test Client",
                            client_email="client@test.com",
                            meeting_type='VIDEO',
                        )
                        
                        if mock_task.called:
                            print("SUCCESS: create_google_meet_link_task.delay was called!")
                            print(f"Task called with booking_id: {mock_task.call_args[0][0]}")
                        else:
                            print("FAILURE: create_google_meet_link_task.delay was NOT called.")

if __name__ == "__main__":
    test_booking_logic_simple()
