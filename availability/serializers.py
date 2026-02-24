from rest_framework import serializers
from .models import AvailabilitySlot


class AvailabilitySlotSerializer(serializers.ModelSerializer):
    day_name = serializers.SerializerMethodField()

    class Meta:
        model = AvailabilitySlot
        fields = ('id', 'admin', 'date', 'start_time', 'end_time',
                  'is_booked', 'day_of_week', 'day_name', 'duration_minutes',
                  'created_at')
        read_only_fields = ('id', 'admin', 'is_booked', 'day_of_week',
                            'day_name', 'duration_minutes', 'created_at')

    def get_day_name(self, obj):
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return days[obj.day_of_week] if obj.day_of_week is not None else ''

    def validate_date(self, value):
        if value.weekday() in (5, 6):
            raise serializers.ValidationError(
                'Cannot create availability slots on Saturday or Sunday.'
            )
        return value

    def validate(self, attrs):
        if attrs.get('start_time') and attrs.get('end_time'):
            if attrs['start_time'] >= attrs['end_time']:
                raise serializers.ValidationError(
                    {'end_time': 'End time must be after start time.'}
                )
        return attrs


class AvailabilitySlotCreateSerializer(serializers.ModelSerializer):
    duration_minutes = serializers.IntegerField(required=False, min_value=1, allow_null=True)

    class Meta:
        model = AvailabilitySlot
        fields = ('date', 'start_time', 'end_time', 'duration_minutes')

    def validate_date(self, value):
        if value.weekday() in (5, 6):
            raise serializers.ValidationError(
                'Cannot create availability slots on Saturday or Sunday.'
            )
        return value

    def validate(self, attrs):
        if attrs['start_time'] >= attrs['end_time']:
            raise serializers.ValidationError(
                {'end_time': 'End time must be after start time.'}
            )
        return attrs
