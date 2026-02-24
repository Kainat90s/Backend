from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache


class AvailabilitySlot(models.Model):
    """A time slot during which the admin is available for bookings."""

    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='availability_slots',
    )
    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_booked = models.BooleanField(default=False, db_index=True)
    day_of_week = models.IntegerField(
        choices=WEEKDAY_CHOICES,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'availability_slot'
        ordering = ['date', 'start_time']
        verbose_name = 'Availability Slot'
        verbose_name_plural = 'Availability Slots'
        indexes = [
            models.Index(fields=['date', 'is_booked']),
            models.Index(fields=['admin', 'date']),
        ]

    def __str__(self):
        day_name = dict(self.WEEKDAY_CHOICES).get(self.day_of_week, '')
        return f'{self.date} ({day_name}) {self.start_time}–{self.end_time}'

    def save(self, *args, **kwargs):
        # Auto-compute day_of_week from date
        self.day_of_week = self.date.weekday()
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        """Validate slot: no weekends, no overlap, times are correct."""
        # Auto-set day_of_week before validation
        if self.date:
            self.day_of_week = self.date.weekday()

        # Weekend check
        if self.day_of_week in (5, 6):
            raise ValidationError(
                'Cannot create availability slots on Saturday or Sunday.'
            )

        # Time order check
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError(
                'Start time must be before end time.'
            )

        # Overlap check
        if self.date and self.start_time and self.end_time:
            overlapping = AvailabilitySlot.objects.filter(
                admin=self.admin,
                date=self.date,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError(
                    'This slot overlaps with an existing availability slot.'
                )

    @property
    def duration_minutes(self):
        """Return the slot duration in minutes."""
        from datetime import datetime
        start_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(self.date, self.end_time)
        return int((end_dt - start_dt).total_seconds() / 60)

@receiver([post_save, post_delete], sender=AvailabilitySlot)
def clear_availability_cache(sender, **kwargs):
    cache.clear()
