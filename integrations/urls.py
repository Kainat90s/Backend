from django.urls import path
from . import views

app_name = 'integrations'

urlpatterns = [
    path('google/auth/', views.GoogleOAuthInitView.as_view(), name='google-oauth-init'),
    path('google/callback/', views.GoogleOAuthCallbackView.as_view(), name='google-oauth-callback'),
    path('google/status/', views.GoogleOAuthStatusView.as_view(), name='google-oauth-status'),
    path('google/disconnect/', views.GoogleOAuthDisconnectView.as_view(), name='google-oauth-disconnect'),
]
