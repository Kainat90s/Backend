import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Prevent celery auto-import
sys.modules['celery'] = type(sys)('celery')

import django
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()
admin_email = 'admin@byteslot.com'

if not User.objects.filter(email__iexact=admin_email).exists():
    user = User()
    user.email = admin_email
    user.username = admin_email
    user.set_password('admin123')
    user.is_superuser = True
    user.is_staff = True
    user.role = 'admin'
    user.save()
    print('Superuser created successfully!')
    print(f'Email: {admin_email}')
    print('Password: admin123')
else:
    print('Admin user already exists!')
