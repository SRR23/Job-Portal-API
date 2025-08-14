import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_portal.settings')

# Create Celery instance and configure it using the settings from Django.
app = Celery('job_portal')

# Load task modules from all registered Django app configs.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Debug: Print the broker URL to verify it's being loaded correctly.
print(f"CELERY_BROKER_URL: {app.conf.broker_url}")

# Auto-discover tasks in all installed apps.
app.autodiscover_tasks()