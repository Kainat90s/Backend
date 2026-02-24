from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SystemSettings
from .serializers import SystemSettingsSerializer, DashboardSerializer
from .services import DashboardService


class SystemSettingsView(APIView):
    """GET / PUT the global system settings (admin only)."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        settings = SystemSettings.load()
        serializer = SystemSettingsSerializer(settings)
        return Response(serializer.data)

    def put(self, request):
        settings = SystemSettings.load()
        serializer = SystemSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie

class DashboardView(APIView):
    """Admin dashboard: weekly hours, upcoming meetings, stats."""
    permission_classes = (IsAuthenticated,)

    @method_decorator(cache_page(60 * 1)) # Cache for 1 minute
    @method_decorator(vary_on_cookie)
    def get(self, request):
        data = {
            'weekly_hours': DashboardService.get_weekly_available_hours(),
            'upcoming_meetings': DashboardService.get_upcoming_meetings(),
            'stats': DashboardService.get_weekly_stats(),
        }
        serializer = DashboardSerializer(data)
        return Response(serializer.data)
