from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import redirect
from django.utils.html import format_html
from .models import Booking
from .services import BookingService


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'client_name', 'client_email', 'status', 
                    'slot', 'approve_button', 'created_at')
    list_filter = ('status', 'meeting_type', 'created_at')
    search_fields = ('client_name', 'client_email')
    ordering = ('-created_at',)
    readonly_fields = ('meet_link', 'created_at', 'updated_at')
    actions = ['approve_bookings_action', 'cancel_bookings_action']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:booking_id>/approve-direct/', self.approve_direct, name='booking-approve-direct'),
        ]
        return custom_urls + urls

    def approve_button(self, obj):
        if obj.status == Booking.Status.PENDING:
            return format_html(
                '<a class="button" href="{}" style="background: #10b981; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;">Approve Now</a>',
                f'./{obj.id}/approve-direct/'
            )
        return obj.get_status_display()
    approve_button.short_description = 'Quick Action'

    def approve_direct(self, request, booking_id):
        try:
            BookingService.approve_booking(booking_id)
            self.message_user(request, "Booking approved successfully.", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Error: {str(e)}", level=messages.ERROR)
        return redirect('..')

    @admin.action(description="Approve selected bookings")
    def approve_bookings_action(self, request, queryset):
        count = 0
        for booking in queryset:
            try:
                BookingService.approve_booking(booking.id)
                count += 1
            except Exception:
                pass
        self.message_user(request, f"{count} bookings approved.", level=messages.SUCCESS)

    @admin.action(description="Cancel selected bookings")
    def cancel_bookings_action(self, request, queryset):
        count = 0
        queryset.update(status=Booking.Status.CANCELLED) # Simplified for bulk
        self.message_user(request, "Selected bookings cancelled.", level=messages.SUCCESS)
