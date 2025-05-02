import os
from celery.utils.log import get_task_logger

from celery import Celery


app = Celery(__name__)
app.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
app.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")
logger = get_task_logger(__name__)

app.autodiscover_tasks(['calculations.catchment','calculations.isozones'])