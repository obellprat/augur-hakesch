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