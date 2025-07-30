# job_board/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_portal.settings')

app = Celery('job_portal')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()