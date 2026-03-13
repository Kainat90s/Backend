from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Booking
from .serializers import BookingSerializer, BookingCreateSerializer
from .services import BookingService


class BookingCreateView(APIView):
    """Create a new booking (public — clients don't need auth)."""
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        client_user = request.user if request.user.is_authenticated else None

        booking = BookingService.create_booking(
            slot_id=serializer.validated_data['slot_id'],
            client_name=serializer.validated_data['client_name'],
            client_email=serializer.validated_data['client_email'],
            meeting_type=serializer.validated_data['meeting_type'],
            notes=serializer.validated_data.get('notes', ''),
            client_user=client_user,
            custom_start=serializer.validated_data.get('start_time'),
            custom_end=serializer.validated_data.get('end_time'),
            public_slug=serializer.validated_data.get('public_slug'),
        )

        return Response(
            BookingSerializer(booking).data,
            status=status.HTTP_201_CREATED,
        )


class BookingListView(generics.ListAPIView):
    """Admin: list all bookings."""
    serializer_class = BookingSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        qs = Booking.objects.select_related('slot').all()

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        # Filter by date range
        from_date = self.request.query_params.get('from_date')
        to_date = self.request.query_params.get('to_date')
        if from_date:
            qs = qs.filter(slot__date__gte=from_date)
        if to_date:
            qs = qs.filter(slot__date__lte=to_date)

        return qs.order_by('-created_at')


class BookingDetailView(generics.RetrieveAPIView):
    """View a specific booking."""
    serializer_class = BookingSerializer
    permission_classes = (IsAuthenticated,)
    queryset = Booking.objects.select_related('slot').all()


class BookingCancelView(APIView):
    """Cancel a booking."""
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        booking = BookingService.cancel_booking(
            booking_id=pk,
            user=request.user,
        )
        return Response(BookingSerializer(booking).data)


class BookingApproveView(APIView):
    """Admin: Approve a pending booking."""
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        if not request.user.role == 'admin':
            return Response({'detail': 'Only admins can approve bookings.'}, status=status.HTTP_403_FORBIDDEN)
            
        booking = BookingService.approve_booking(
            booking_id=pk,
            user=request.user,
        )
        return Response(BookingSerializer(booking).data)


class BookingStatusUpdateView(APIView):
    """Admin: Update booking status (Pending, Confirmed, Cancelled)."""
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        if not request.user.role == 'admin':
            return Response({'detail': 'Only admins can update booking status.'}, status=status.HTTP_403_FORBIDDEN)
        
        status_val = request.data.get('status')
        if not status_val:
            return Response({'detail': 'Status is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        booking = BookingService.update_booking_status(
            booking_id=pk,
            status=status_val,
            user=request.user,
        )
        return Response(BookingSerializer(booking).data)


class MyBookingsView(generics.ListAPIView):
    """Client: list only the logged-in user's bookings."""
    serializer_class = BookingSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        qs = Booking.objects.select_related('slot').filter(
            client=self.request.user
        )

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        return qs.order_by('-slot__date', '-slot__start_time')
