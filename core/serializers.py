from rest_framework import serializers
from .models import SystemSettings


class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = ('meeting_duration', 'buffer_before_minutes',
                  'buffer_after_minutes', 'weekend_off',
                  'email_host', 'email_port', 'email_use_tls',
                  'email_host_user', 'email_host_password',
                  'default_from_email', 'updated_at')
        read_only_fields = ('updated_at',)


class WeeklyHoursSerializer(serializers.Serializer):
    day = serializers.CharField()
    date = serializers.DateField()
    hours = serializers.FloatField()
    is_off = serializers.BooleanField()


class UpcomingMeetingSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    client_name = serializers.CharField()
    date = serializers.DateField()
    time = serializers.TimeField()
    meeting_type = serializers.CharField()
    status = serializers.CharField()


class DashboardStatsSerializer(serializers.Serializer):
    total_bookings_this_week = serializers.IntegerField()
    available_slots_remaining = serializers.IntegerField()
    confirmed_bookings = serializers.IntegerField()
    cancelled_bookings = serializers.IntegerField()


class DashboardSerializer(serializers.Serializer):
    weekly_hours = WeeklyHoursSerializer(many=True)
    upcoming_meetings = UpcomingMeetingSerializer(many=True)
    stats = DashboardStatsSerializer()
