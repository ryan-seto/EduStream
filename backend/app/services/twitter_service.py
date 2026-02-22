"""
Twitter/X publishing service.
Uses tweepy for API v2 with OAuth 1.0a for media uploads.
"""
import tweepy
from pathlib import Path

from app.config import get_settings

settings = get_settings()


class TwitterService:
    """Service for publishing content to Twitter/X."""

    def __init__(self):
        self.client = None
        self.api_v1 = None
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of Twitter clients."""
        if self._initialized:
            return

        if not all([
            settings.twitter_api_key,
            settings.twitter_api_secret,
            settings.twitter_access_token,
            settings.twitter_access_token_secret,
        ]):
            raise ValueError(
                "Twitter API credentials not configured. "
                "Please set TWITTER_API_KEY, TWITTER_API_SECRET, "
                "TWITTER_ACCESS_TOKEN, and TWITTER_ACCESS_TOKEN_SECRET in .env"
            )

        # OAuth 1.0a authentication for media uploads (API v1.1)
        auth = tweepy.OAuth1UserHandler(
            settings.twitter_api_key,
            settings.twitter_api_secret,
            settings.twitter_access_token,
            settings.twitter_access_token_secret,
        )
        self.api_v1 = tweepy.API(auth)

        # API v2 client for tweeting
        self.client = tweepy.Client(
            consumer_key=settings.twitter_api_key,
            consumer_secret=settings.twitter_api_secret,
            access_token=settings.twitter_access_token,
            access_token_secret=settings.twitter_access_token_secret,
        )

        self._initialized = True

    def is_configured(self) -> bool:
        """Check if Twitter credentials are configured."""
        return all([
            settings.twitter_api_key,
            settings.twitter_api_secret,
            settings.twitter_access_token,
            settings.twitter_access_token_secret,
        ])

    async def post_image(
        self,
        image_path: str,
        caption: str,
        hashtags: list[str] | None = None,
    ) -> dict:
        """
        Post an image to Twitter/X.

        Args:
            image_path: Path to the image file
            caption: Tweet text
            hashtags: Optional list of hashtags to append

        Returns:
            dict with tweet_id and url
        """
        self._ensure_initialized()

        path = Path(image_path)
        temp_file = None

        # If path doesn't exist locally, try downloading from S3
        if not path.exists() and settings.use_s3:
            from app.services.s3_service import s3_service
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            temp_file.close()
            s3_service.download_file(image_path, temp_file.name)
            path = Path(temp_file.name)

        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Build tweet text with hashtags
        tweet_text = caption
        if hashtags:
            hashtag_str = " ".join(f"#{tag.lstrip('#')}" for tag in hashtags)
            tweet_text = f"{caption}\n\n{hashtag_str}"

        # Twitter character limit is 280
        if len(tweet_text) > 280:
            # Truncate caption to fit
            max_caption_len = 280 - len(hashtag_str) - 3 if hashtags else 277
            tweet_text = caption[:max_caption_len] + "..."
            if hashtags:
                tweet_text += f"\n\n{hashtag_str}"

        try:
            # Upload media using v1.1 API (required for media)
            media = self.api_v1.media_upload(filename=str(path))

            # Post tweet with media using v2 API
            response = self.client.create_tweet(
                text=tweet_text,
                media_ids=[media.media_id],
            )

            tweet_id = response.data["id"]

            return {
                "tweet_id": tweet_id,
                "url": f"https://twitter.com/i/status/{tweet_id}",
                "text": tweet_text,
            }
        finally:
            # Clean up temp file if we downloaded from S3
            if temp_file:
                import os
                os.unlink(temp_file.name)

    async def post_text(self, text: str) -> dict:
        """Post a text-only tweet."""
        self._ensure_initialized()

        if len(text) > 280:
            text = text[:277] + "..."

        response = self.client.create_tweet(text=text)
        tweet_id = response.data["id"]

        return {
            "tweet_id": tweet_id,
            "url": f"https://twitter.com/i/status/{tweet_id}",
            "text": text,
        }


# Singleton instance
twitter_service = TwitterService()
