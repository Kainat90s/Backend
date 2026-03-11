import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Prevent celery auto-import
sys.modules['celery'] = type(sys)('celery')

import django
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

if not User.objects.filter(username='admin').exists():
    user = User()
    user.username = 'admin'
    user.email = 'admin@byteslot.com'
    user.set_password('admin123')
    user.is_superuser = True
    user.is_staff = True
    user.role = 'admin'
    user.save()
    print('Superuser created successfully!')
    print('Username: admin')
    print('Password: admin123')
else:
    print('Admin user already exists!')
