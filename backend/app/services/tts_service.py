import logging
import edge_tts
import asyncio
from pathlib import Path
import uuid

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TTSService:
    """
    Text-to-Speech service using Microsoft Edge TTS (free).
    Includes retry logic for handling transient failures.
    """

    # Good voices for educational content
    VOICES = {
        "male_us": "en-US-GuyNeural",
        "female_us": "en-US-JennyNeural",
        "male_uk": "en-GB-RyanNeural",
        "female_uk": "en-GB-SoniaNeural",
    }

    def __init__(self):
        self.output_dir = Path(settings.output_dir) / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_audio(
        self,
        text: str,
        voice: str = "male_us",
        rate: str = "+0%",  # Speed adjustment: -50% to +50%
        pitch: str = "+0Hz",  # Pitch adjustment
        max_retries: int = 3,
    ) -> str:
        """
        Generate audio from text using Edge TTS with retry logic.

        Args:
            text: The text to convert to speech
            voice: Voice preset (male_us, female_us, male_uk, female_uk)
            rate: Speaking rate adjustment
            pitch: Pitch adjustment
            max_retries: Number of retries on failure

        Returns:
            Path to the generated audio file
        """
        voice_name = self.VOICES.get(voice, self.VOICES["male_us"])
        output_file = self.output_dir / f"{uuid.uuid4()}.mp3"

        last_error = None
        for attempt in range(max_retries):
            try:
                communicate = edge_tts.Communicate(
                    text,
                    voice_name,
                    rate=rate,
                    pitch=pitch,
                )
                await communicate.save(str(output_file))
                return str(output_file)
            except Exception as e:
                last_error = e
                logger.warning("TTS attempt %d/%d failed: %s", attempt + 1, max_retries, e)
                if attempt < max_retries - 1:
                    # Wait before retry (exponential backoff)
                    await asyncio.sleep(2 ** attempt)

        # If all retries failed, try alternative voices
        alternative_voices = ["en-US-AriaNeural", "en-US-ChristopherNeural"]
        for alt_voice in alternative_voices:
            try:
                logger.info("Trying alternative voice: %s", alt_voice)
                communicate = edge_tts.Communicate(text, alt_voice, rate=rate, pitch=pitch)
                await communicate.save(str(output_file))
                return str(output_file)
            except Exception as e:
                logger.warning("Alternative voice %s failed: %s", alt_voice, e)
                continue

        # Final fallback: use gTTS (Google Text-to-Speech)
        try:
            logger.info("Falling back to gTTS...")
            from gtts import gTTS
            tts = gTTS(text=text, lang='en')
            tts.save(str(output_file))
            return str(output_file)
        except Exception as gtts_error:
            logger.error("gTTS fallback also failed: %s", gtts_error)

        raise Exception(f"TTS failed after {max_retries} retries and gTTS fallback: {last_error}")

    async def get_audio_duration(self, audio_path: str) -> float:
        """Get the duration of an audio file in seconds."""
        try:
            from moviepy.editor import AudioFileClip

            clip = AudioFileClip(audio_path)
            duration = clip.duration
            clip.close()
            return duration
        except Exception:
            # Estimate based on text length if moviepy fails
            return 0.0

    @staticmethod
    async def list_voices() -> list[dict]:
        """List all available voices."""
        voices = await edge_tts.list_voices()
        return [
            {
                "name": v["Name"],
                "gender": v["Gender"],
                "locale": v["Locale"],
            }
            for v in voices
            if v["Locale"].startswith("en-")
        ]


# Singleton instance
tts_service = TTSService()
