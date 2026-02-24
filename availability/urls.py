from django.urls import path
from . import views

app_name = 'availability'

urlpatterns = [
    path('slots/', views.AvailabilitySlotListView.as_view(), name='slot-list'),
    path('admin/slots/', views.AvailabilitySlotAdminView.as_view(), name='admin-slot-list'),
    path('admin/slots/<int:pk>/', views.AvailabilitySlotDetailView.as_view(), name='admin-slot-detail'),
    path('admin/slots/bulk-delete/<str:date>/', views.BulkDeleteDayView.as_view(), name='admin-bulk-delete-day'),
]
