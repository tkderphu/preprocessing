"""
celery_app.py
-------------
Celery application configuration.
Broker: RabbitMQ (AMQP)
Backend: Redis (for result storage / polling)
"""

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "doc_intelligence",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Task routing — all tasks go to the document_jobs queue
    task_default_queue=settings.celery_queue_name,
    task_routes={
        "app.worker.tasks.process_document_job": {
            "queue": settings.celery_queue_name,
        },
    },

    # Reliability
    task_acks_late=True,           # Ack only after task completes
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # One task at a time (ML models are heavy)

    # Timeouts
    task_soft_time_limit=1800,     # 30 min soft limit (warning)
    task_time_limit=2400,          # 40 min hard limit (kill)

    # Result TTL
    result_expires=86400,          # Keep results for 24 hours
)
