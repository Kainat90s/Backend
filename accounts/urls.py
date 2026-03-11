from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.views import TokenRefreshView

from . import views
from .auth_views import JsonPasswordResetView, JsonPasswordResetConfirmView

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('register/otp/request/', views.RequestRegistrationOTPView.as_view(), name='register-otp-request'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('password-reset/', csrf_exempt(JsonPasswordResetView.as_view(
        email_template_name='emails/password_reset_email.txt',
        html_email_template_name='emails/password_reset_email.html',
        subject_template_name='emails/password_reset_subject.txt',
    )), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', csrf_exempt(JsonPasswordResetConfirmView.as_view()), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('password-reset/request/', views.RequestPasswordResetView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', views.ConfirmPasswordResetView.as_view(), name='password-reset-confirm'),
    # Management
    path('manage/users/', views.UserManagementView.as_view(), name='user-list'),
    path('manage/users/<int:pk>/', views.UserDetailManagementView.as_view(), name='user-detail'),
]
