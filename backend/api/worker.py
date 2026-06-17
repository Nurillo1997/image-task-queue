from celery import Celery

from api.config import settings

celery_app = Celery(
    "image_worker",
    broker=settings.rabbitmq_url,
    backend="rpc://",
)

celery_app.autodiscover_tasks(["api"])

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
