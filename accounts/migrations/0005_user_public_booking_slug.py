from django.db import migrations, models
from django.utils.text import slugify
import uuid


def create_public_booking_slugs(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.all():
        if user.role != 'admin' and not user.is_superuser:
            continue
        if user.public_booking_slug:
            continue

        full_name = f"{user.first_name} {user.last_name}".strip()
        email_prefix = user.email.split('@')[0] if user.email else ''
        base = slugify(full_name or email_prefix or user.username or 'admin') or 'admin'
        slug = base
        if User.objects.filter(public_booking_slug=slug).exclude(pk=user.pk).exists():
            slug = f"{base}-{uuid.uuid4().hex[:6]}"
        user.public_booking_slug = slug
        user.save(update_fields=['public_booking_slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_registrationotp'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='public_booking_slug',
            field=models.SlugField(blank=True, help_text='Public booking link slug for admins.', max_length=64, null=True, unique=True),
        ),
        migrations.RunPython(create_public_booking_slugs, migrations.RunPython.noop),
    ]
