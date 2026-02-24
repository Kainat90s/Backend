"""
Root URL configuration for ByteSlot.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),
    path('api/core/', include('core.urls')),
    path('api/availability/', include('availability.urls')),
    path('api/bookings/', include('bookings.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/integrations/', include('integrations.urls')),
]
