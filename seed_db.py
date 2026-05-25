import os
import django

# Set up the Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from emissions.models import Company

# 1. Automatically create the superuser if it doesn't exist
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'Breathe2026!')
    print("✅ Superuser 'admin' created automatically.")

# 2. Automatically create the test company
if not Company.objects.filter(name='ABC Construction PVT. LTD').exists():
    Company.objects.create(name='ABC Construction PVT. LTD')
    print("✅ Test Company 'ABC Construction' created automatically.")