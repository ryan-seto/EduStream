"""
SQS queue service for scheduled tweet publishing.
Uses boto3 directly.
"""
import json
import logging
import boto3
from datetime import datetime

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SQSService:
    """Wraps boto3 SQS client for tweet publishing queue."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        """Lazy-init boto3 SQS client."""
        if self._client is None:
            self._client = boto3.client(
                "sqs",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region,
            )
        return self._client

    def enqueue_publish(
        self,
        content_id: int,
        platform: str,
        caption: str,
        image_path: str,
        scheduled_at: datetime | None = None,
    ) -> str:
        """
        Send a publish job to SQS.

        Uses DelaySeconds for near-future scheduling (max 15 min).
        For longer delays, the message body includes scheduled_at and the
        worker checks before processing.

        Returns:
            SQS MessageId.
        """
        message_body = {
            "content_id": content_id,
            "platform": platform,
            "caption": caption,
            "image_path": image_path,
            "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
            "enqueued_at": datetime.utcnow().isoformat(),
        }

        delay_seconds = 0
        if scheduled_at:
            delta = (scheduled_at - datetime.utcnow()).total_seconds()
            if 0 < delta <= 900:
                delay_seconds = int(delta)

        response = self.client.send_message(
            QueueUrl=settings.sqs_queue_url,
            MessageBody=json.dumps(message_body),
            DelaySeconds=delay_seconds,
        )
        msg_id = response["MessageId"]
        logger.info("Enqueued content %d (MessageId: %s)", content_id, msg_id)
        return msg_id

    def receive_messages(self, max_messages: int = 1) -> list[dict]:
        """
        Poll SQS for messages. Long-polling with 20s wait.

        Returns:
            List of dicts with receipt_handle, body, and message_id.
        """
        response = self.client.receive_message(
            QueueUrl=settings.sqs_queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=20,
            VisibilityTimeout=300,
        )
        messages = response.get("Messages", [])
        return [
            {
                "receipt_handle": m["ReceiptHandle"],
                "body": json.loads(m["Body"]),
                "message_id": m["MessageId"],
            }
            for m in messages
        ]

    def delete_message(self, receipt_handle: str) -> None:
        """Delete a message after successful processing."""
        self.client.delete_message(
            QueueUrl=settings.sqs_queue_url,
            ReceiptHandle=receipt_handle,
        )

    def get_queue_attributes(self) -> dict:
        """Get queue stats (approximate message count, etc.)."""
        response = self.client.get_queue_attributes(
            QueueUrl=settings.sqs_queue_url,
            AttributeNames=[
                "ApproximateNumberOfMessages",
                "ApproximateNumberOfMessagesNotVisible",
            ],
        )
        return response.get("Attributes", {})


sqs_service = SQSService()
