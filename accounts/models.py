from django.contrib.auth.models import AbstractUser
from django.db import models


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

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.role})'

    def save(self, *args, **kwargs):
        # Auto-set role to admin for superusers
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN or self.is_superuser
