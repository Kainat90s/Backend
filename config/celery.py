"""
Celery configuration for ByteSlot project.
"""

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('byteslot')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# ---------------------------------------------------------------------------
# Periodic tasks (Celery Beat)
# ---------------------------------------------------------------------------
app.conf.beat_schedule = {
    'send-meeting-reminders': {
        'task': 'notifications.tasks.send_upcoming_reminders',
        'schedule': crontab(minute='*/15'),  # every 15 minutes
    },
}
