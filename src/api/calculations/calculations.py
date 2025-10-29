from logging.handlers import RotatingFileHandler
import os
from celery.utils.log import get_task_logger
from celery import signals
import logging

from celery import Celery

from pathlib import Path

app = Celery(__name__)
app.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
app.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")
app.conf.worker_redirect_stdouts = False

# Performance optimizations for faster task startup and execution
# Reduce prefetch to prevent tasks from being held while waiting for I/O
app.conf.worker_prefetch_multiplier = 1
# Acknowledge tasks late to prevent loss if worker crashes during execution
app.conf.task_acks_late = True
# Reject tasks that fail on retry to prevent infinite retries
app.conf.task_reject_on_worker_lost = True
# Compress messages to reduce broker overhead
app.conf.task_compression = 'gzip'
app.conf.result_compression = 'gzip'
# Enable connection retry on startup for better reliability
app.conf.broker_connection_retry_on_startup = True
# Optimize broker connection pool
app.conf.broker_pool_limit = 10
app.conf.broker_connection_max_retries = 10
# Optimize task serialization
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']
# Reduce task message overhead
app.conf.task_message_max_retries = 3
# Optimize result backend for faster lookups
app.conf.result_expires = 3600  # Results expire after 1 hour

logger = get_task_logger(__name__)
logging.getLogger('prisma').setLevel(logging.ERROR)

def create_celery_logger_handler(logger, propagate):
    # 209715200 is 1024 * 1024 * 200 or 200 MB, same as in settings
    celery_handler = RotatingFileHandler(
        Path("logs/celery.log"),
        maxBytes=209715200,
        backupCount=10
    )

    logger.addHandler(celery_handler)
    logger.logLevel = "INFO"
    logger.propagate = propagate


@signals.after_setup_task_logger.connect
def after_setup_celery_task_logger(logger, **kwargs):
    """ This function sets the 'celery.task' logger handler and formatter """
    create_celery_logger_handler(logger, True)


@signals.after_setup_logger.connect
def after_setup_celery_logger(logger, **kwargs):
    """ This function sets the 'celery' logger handler and formatter """
    create_celery_logger_handler(logger, False)

app.autodiscover_tasks(['calculations.discharge','calculations.nam','calculations.curvenumbers'])