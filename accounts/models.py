from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify
import uuid


class User(AbstractUser):
    """Custom user model for ByteSlot."""

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        CLIENT = 'client', 'Client'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.CLIENT,
        db_index=True,
    )
    phone = models.CharField(max_length=20, blank=True, default='')

    # Google OAuth tokens (stored on admin accounts for Meet integration)
    google_oauth_token = models.JSONField(null=True, blank=True)
    google_refresh_token = models.TextField(blank=True, default='')

    public_booking_slug = models.SlugField(
        max_length=64,
        unique=True,
        blank=True,
        null=True,
        help_text='Public booking link slug for admins.',
    )

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f'{self.get_full_name() or self.email} ({self.role})'

    def save(self, *args, **kwargs):
        if not self.username and self.email:
            self.username = self.email
        # Auto-set role to admin for superusers
        if self.is_superuser:
            self.role = self.Role.ADMIN
        if self.role == self.Role.ADMIN and not self.public_booking_slug:
            email_prefix = self.email.split('@')[0] if self.email else ''
            base = slugify(self.get_full_name() or email_prefix or self.username or 'admin')
            base = base or 'admin'
            slug = base
            if User.objects.filter(public_booking_slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{uuid.uuid4().hex[:6]}"
            self.public_booking_slug = slug
        super().save(*args, **kwargs)

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN or self.is_superuser


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=6)  # 6-digit PIN
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = 'accounts_password_reset_token'
        ordering = ['-created_at']

    def __str__(self):
        return f"Reset code for {self.user.email} - {self.token}"

    def is_expired(self):
        from django.utils import timezone
        from datetime import timedelta
        # Expire after 15 minutes
        return timezone.now() > self.created_at + timedelta(minutes=15)


class RegistrationOTP(models.Model):
    email = models.EmailField()
    token = models.CharField(max_length=6)  # 6-digit PIN
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = 'accounts_registration_otp'
        ordering = ['-created_at']

    def __str__(self):
        return f"Registration OTP for {self.email} - {self.token}"

    def is_expired(self):
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() > self.created_at + timedelta(minutes=10)
