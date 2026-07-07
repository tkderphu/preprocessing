"""
queue.py
--------
Publish job messages to RabbitMQ using aio-pika (async).
"""

import json
import logging

import aio_pika

from app.config import get_settings
from app.models.schemas import JobMessage

logger = logging.getLogger(__name__)
settings = get_settings()


async def publish_job(job: JobMessage) -> None:
    """
    Publish a JobMessage to the RabbitMQ document_jobs queue.
    The message is persistent so it survives broker restarts.
    """
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)

    async with connection:
        channel = await connection.channel()

        queue = await channel.declare_queue(
            settings.celery_queue_name,
            durable=True,
        )

        body = job.model_dump_json().encode()

        await channel.default_exchange.publish(
            aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            ),
            routing_key=queue.name,
        )

        logger.info(
            "Published job %s (%s) to queue '%s'",
            job.job_id, job.file_name, settings.celery_queue_name,
        )
