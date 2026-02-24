from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('logs/', views.NotificationLogListView.as_view(), name='notification-logs'),
]
