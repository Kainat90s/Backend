from django.contrib import admin
from .models import SystemSettings


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('meeting_duration', 'buffer_before_minutes', 'buffer_after_minutes', 'weekend_off', 'updated_at')

    def has_add_permission(self, request):
        # Only allow one instance (singleton)
        return not SystemSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
