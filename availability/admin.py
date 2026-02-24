from django.contrib import admin
from django.db import models
from django.forms import TimeInput
from .models import AvailabilitySlot


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ('date', 'start_time', 'end_time', 'admin', 'is_booked', 'day_of_week')
    list_filter = ('date', 'is_booked', 'day_of_week')
    search_fields = ('admin__username', 'admin__email')
    ordering = ('date', 'start_time')
    readonly_fields = ('day_of_week',)

    formfield_overrides = {
        models.TimeField: {'widget': TimeInput(attrs={'type': 'time', 'class': 'vTimeField'})},
    }
