from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import NotificationLog
from .serializers import NotificationLogSerializer


class NotificationLogListView(generics.ListAPIView):
    """Admin: view notification history."""
    serializer_class = NotificationLogSerializer
    permission_classes = (IsAuthenticated,)
    queryset = NotificationLog.objects.all().order_by('-sent_at')
