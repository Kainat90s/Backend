from rest_framework import serializers
from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    slot_date = serializers.DateField(source='slot.date', read_only=True)
    slot_start_time = serializers.TimeField(source='slot.start_time', read_only=True)
    slot_end_time = serializers.TimeField(source='slot.end_time', read_only=True)

    class Meta:
        model = Booking
        fields = ('id', 'slot', 'slot_date', 'slot_start_time', 'slot_end_time',
                  'client', 'client_name', 'client_email', 'meeting_type',
                  'status', 'meet_link', 'notes', 'created_at', 'updated_at')
        read_only_fields = ('id', 'client', 'status', 'meet_link',
                            'created_at', 'updated_at')


class BookingCreateSerializer(serializers.Serializer):
    slot_id = serializers.IntegerField()
    client_name = serializers.CharField(max_length=150)
    client_email = serializers.EmailField()
    meeting_type = serializers.ChoiceField(choices=Booking.MeetingType.choices)
    public_slug = serializers.SlugField(required=False, allow_blank=True, allow_null=True)
    start_time = serializers.TimeField(required=False, allow_null=True)
    end_time = serializers.TimeField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
