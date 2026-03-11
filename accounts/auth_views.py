import json

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetConfirmView,
    INTERNAL_RESET_SESSION_TOKEN,
)
from django.conf import settings
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


def _parse_json_body(request):
    if request.content_type != 'application/json':
        return None
    try:
        raw = request.body.decode('utf-8') if request.body else ''
        return json.loads(raw) if raw else {}
    except (ValueError, UnicodeDecodeError):
        return {}


def _get_frontend_base(request):
    origin = request.META.get('HTTP_ORIGIN')
    if origin:
        return origin.rstrip('/')
    cors_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
    if cors_origins:
        return str(cors_origins[0]).rstrip('/')
    scheme = 'https' if request.is_secure() else 'http'
    return f"{scheme}://{request.get_host()}"


class StrictPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            return email
        user_exists = get_user_model().objects.filter(email__iexact=email, is_active=True).exists()
        if not user_exists:
            raise ValidationError('No account is associated with this email address.')
        return email


@method_decorator(csrf_exempt, name='dispatch')
class JsonPasswordResetView(PasswordResetView):
    form_class = StrictPasswordResetForm
    # PasswordResetView is csrf_protect-decorated. Override dispatch to bypass it for API usage.
    def dispatch(self, request, *args, **kwargs):
        return super(PasswordResetView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        data = _parse_json_body(self.request)
        if data is not None:
            kwargs['data'] = data
        return kwargs

    def form_valid(self, form):
        super().form_valid(form)
        return JsonResponse({'detail': 'Password reset email sent.'})

    def form_invalid(self, form):
        return JsonResponse(form.errors, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class JsonPasswordResetConfirmView(PasswordResetConfirmView):
    # PasswordResetConfirmView is csrf_protect-decorated. Implement a CSRF-free dispatch
    # while preserving token validation and user binding.
    def dispatch(self, *args, **kwargs):
        if "uidb64" not in kwargs or "token" not in kwargs:
            raise ImproperlyConfigured(
                "The URL path must contain 'uidb64' and 'token' parameters."
            )

        self.validlink = False
        self.user = self.get_user(kwargs["uidb64"])

        if self.user is not None:
            token = kwargs["token"]
            if self.token_generator.check_token(self.user, token):
                self.validlink = True
                # Match Django's expected session token to avoid KeyError on save.
                self.request.session[INTERNAL_RESET_SESSION_TOKEN] = token
                return super(PasswordResetConfirmView, self).dispatch(*args, **kwargs)

        return self.render_to_response(self.get_context_data())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        data = _parse_json_body(self.request)
        if data is not None:
            kwargs['data'] = data
        return kwargs

    def post(self, request, *args, **kwargs):
        if not getattr(self, 'validlink', True):
            return JsonResponse({'detail': 'Invalid or expired reset link.'}, status=400)
        return super().post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        base = _get_frontend_base(request)
        uid = kwargs.get('uidb64')
        token = kwargs.get('token')
        return redirect(f"{base}/password-reset-confirm/{uid}/{token}")

    def form_valid(self, form):
        super().form_valid(form)
        return JsonResponse({'detail': 'Password reset successful.'})

    def form_invalid(self, form):
        return JsonResponse(form.errors, status=400)
