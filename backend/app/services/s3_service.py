"""
S3 storage service for diagram images.
Uses boto3 directly. Falls back to local storage when S3 is not configured.
"""
import logging
import uuid
import boto3
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class S3Service:
    """Wraps boto3 S3 client for diagram image storage."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        """Lazy-init boto3 S3 client."""
        if self._client is None:
            self._client = boto3.client(
                "s3",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region,
            )
        return self._client

    def upload_file(self, local_path: str, s3_key: str | None = None) -> str:
        """
        Upload a local file to S3.

        Args:
            local_path: Path to the local file.
            s3_key: Optional S3 object key. Auto-generated if not provided.

        Returns:
            The S3 object key (e.g. "diagrams/abc123.png").
        """
        path = Path(local_path)
        if s3_key is None:
            s3_key = f"{settings.s3_prefix}{uuid.uuid4()}.{path.suffix.lstrip('.')}"

        self.client.upload_file(
            Filename=str(path),
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            ExtraArgs={"ContentType": "image/png"},
        )
        logger.info("Uploaded %s -> s3://%s/%s", path.name, settings.s3_bucket_name, s3_key)
        return s3_key

    def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Generate a presigned GET URL for an S3 object."""
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket_name, "Key": s3_key},
            ExpiresIn=expires_in,
        )

    def get_public_url(self, s3_key: str) -> str:
        """
        Get the public URL for an S3 object.
        Uses CloudFront domain if configured, otherwise presigned URL.
        """
        if settings.cloudfront_domain:
            domain = settings.cloudfront_domain.rstrip("/")
            return f"https://{domain}/{s3_key}"
        return self.get_presigned_url(s3_key)

    def download_file(self, s3_key: str, local_path: str) -> str:
        """Download an S3 object to a local file. Needed for Twitter media upload."""
        self.client.download_file(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Filename=local_path,
        )
        return local_path

    def delete_object(self, s3_key: str) -> None:
        """Delete an object from S3."""
        self.client.delete_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
        )


s3_service = S3Service()
