from rest_framework import generics, status, viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound

from .models import AvailabilitySlot
from .serializers import AvailabilitySlotSerializer, AvailabilitySlotCreateSerializer
from .services import AvailabilityService
from accounts.models import User


from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

class AvailabilitySlotListView(generics.ListAPIView):
    """List all available (unbooked) slots — public endpoint."""
    serializer_class = AvailabilitySlotSerializer
    permission_classes = (AllowAny,)
    pagination_class = None

    @method_decorator(cache_page(60 * 1)) # Cache for 1 minute
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        from_date = self.request.query_params.get('from_date')
        to_date = self.request.query_params.get('to_date')
        return AvailabilityService.get_available_slots(from_date, to_date)


class PublicAvailabilityBySlugView(generics.ListAPIView):
    """List available slots for a specific admin public link."""
    serializer_class = AvailabilitySlotSerializer
    permission_classes = (AllowAny,)
    pagination_class = None

    @method_decorator(cache_page(60 * 1)) # Cache for 1 minute
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        from_date = self.request.query_params.get('from_date')
        to_date = self.request.query_params.get('to_date')
        slug = self.kwargs.get('slug')

        admin_exists = User.objects.filter(public_booking_slug=slug, role=User.Role.ADMIN).exists()
        if not admin_exists:
            raise NotFound('Booking link not found.')

        return AvailabilityService.get_available_slots_for_admin_slug(slug, from_date, to_date)


class AvailabilitySlotAdminView(generics.ListCreateAPIView):
    """Admin: list all own slots or create new ones."""
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AvailabilitySlotCreateSerializer
        return AvailabilitySlotSerializer

    def get_queryset(self):
        return AvailabilitySlot.objects.filter(
            admin=self.request.user
        ).order_by('date', 'start_time')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        duration_minutes = serializer.validated_data.get('duration_minutes')
        
        if duration_minutes:
            slots = AvailabilityService.create_slots_range(
                admin_user=self.request.user,
                date=serializer.validated_data['date'],
                start_time=serializer.validated_data['start_time'],
                end_time=serializer.validated_data['end_time'],
                duration_mins=duration_minutes,
            )
            # Return the created slots using the list serializer
            return Response(
                AvailabilitySlotSerializer(slots, many=True).data,
                status=status.HTTP_201_CREATED
            )
        else:
            slot = AvailabilityService.create_slot(
                admin_user=self.request.user,
                date=serializer.validated_data['date'],
                start_time=serializer.validated_data['start_time'],
                end_time=serializer.validated_data['end_time'],
            )
            return Response(
                AvailabilitySlotSerializer(slot).data,
                status=status.HTTP_201_CREATED
            )


class AvailabilitySlotDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin: view, edit, or delete a specific slot."""
    serializer_class = AvailabilitySlotSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return AvailabilitySlot.objects.filter(admin=self.request.user)


class BulkDeleteDayView(generics.GenericAPIView):
    """Admin: delete all slots for a specific date. Auto-cancels bookings."""
    permission_classes = (IsAuthenticated,)
    serializer_class = AvailabilitySlotSerializer  # Required by GenericAPIView

    def delete(self, request, date):
        from datetime import datetime as dt

        # Validate date format
        try:
            parsed_date = dt.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'detail': 'Invalid date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = AvailabilityService.delete_day_slots(
                admin_user=request.user,
                date=parsed_date,
            )
        except Exception as e:
            error_msg = str(e)
            return Response(
                {'detail': error_msg},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result, status=status.HTTP_200_OK)
