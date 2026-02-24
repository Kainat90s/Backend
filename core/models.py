from django.db import models


class SystemSettings(models.Model):
    """
    Singleton model for global scheduling configuration.
    Only one row should ever exist.
    """
    meeting_duration = models.PositiveIntegerField(
        default=30,
        help_text='Default meeting duration in minutes.',
    )
    buffer_before_minutes = models.PositiveIntegerField(
        default=0,
        help_text='Buffer time before a meeting in minutes.',
    )
    buffer_after_minutes = models.PositiveIntegerField(
        default=15,
        help_text='Buffer time after a meeting in minutes.',
    )
    weekend_off = models.BooleanField(
        default=True,
        help_text='If True, Saturday and Sunday are marked as off days.',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_system_settings'
        verbose_name = 'System Settings'
        verbose_name_plural = 'System Settings'

    def __str__(self):
        return f'SystemSettings (duration={self.meeting_duration}min, buffer={self.buffer_before_minutes}/{self.buffer_after_minutes}min)'

    def save(self, *args, **kwargs):
        """Ensure only one instance exists (singleton)."""
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """Load or create the singleton settings instance."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
