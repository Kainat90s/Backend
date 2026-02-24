from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('', views.BookingListView.as_view(), name='booking-list'),
    path('create/', views.BookingCreateView.as_view(), name='booking-create'),
    path('my/', views.MyBookingsView.as_view(), name='my-bookings'),
    path('<int:pk>/', views.BookingDetailView.as_view(), name='booking-detail'),
    path('<int:pk>/cancel/', views.BookingCancelView.as_view(), name='booking-cancel'),
    path('<int:pk>/approve/', views.BookingApproveView.as_view(), name='booking-approve'),
    path('<int:pk>/update-status/', views.BookingStatusUpdateView.as_view(), name='booking-status-update'),
]
