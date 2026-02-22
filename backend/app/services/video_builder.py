from pathlib import Path
import uuid
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, AudioFileClip

from app.config import get_settings

settings = get_settings()


class VideoBuilder:
    """
    Assembles final videos from diagrams and audio using MoviePy/FFmpeg.
    Output format: 9:16 vertical video for TikTok/Instagram Reels/YouTube Shorts
    Uses PIL for text rendering to avoid ImageMagick dependency.
    """

    # Video dimensions for vertical short-form content
    WIDTH = 1080
    HEIGHT = 1920

    # Colors
    BG_COLOR = (26, 26, 46)  # Dark blue background
    TEXT_COLOR = (255, 255, 255)  # White
    ACCENT_COLOR = (78, 204, 163)  # Teal accent

    def __init__(self):
        self.output_dir = Path(settings.output_dir) / "videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(settings.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
        """Wrap text to fit within max_width."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            if bbox[2] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return lines

    def _create_frame_with_text(
        self,
        diagram_path: str,
        title: str,
        cta_text: str = "Follow for more engineering tips!",
    ) -> str:
        """Create a single frame with diagram and text overlays using PIL."""
        # Create base image
        frame = Image.new('RGB', (self.WIDTH, self.HEIGHT), self.BG_COLOR)
        draw = ImageDraw.Draw(frame)

        # Load fonts (use default if Arial not available)
        try:
            title_font = ImageFont.truetype("arial.ttf", 52)
            cta_font = ImageFont.truetype("arial.ttf", 32)
        except OSError:
            try:
                # Try common Linux/Mac paths
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
                cta_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
            except OSError:
                # Fallback to default
                title_font = ImageFont.load_default()
                cta_font = ImageFont.load_default()

        # Draw title at top (wrapped)
        title_lines = self._wrap_text(title, title_font, self.WIDTH - 100)
        y_offset = 80
        for line in title_lines:
            bbox = title_font.getbbox(line)
            text_width = bbox[2] - bbox[0]
            x = (self.WIDTH - text_width) // 2
            draw.text((x, y_offset), line, font=title_font, fill=self.TEXT_COLOR)
            y_offset += bbox[3] - bbox[1] + 10

        # Load and paste diagram in center
        diagram = Image.open(diagram_path)
        # Resize to fit with padding
        max_diagram_width = self.WIDTH - 100
        max_diagram_height = self.HEIGHT - 500  # Leave room for title and CTA
        diagram.thumbnail((max_diagram_width, max_diagram_height), Image.Resampling.LANCZOS)

        # Center the diagram
        diagram_x = (self.WIDTH - diagram.width) // 2
        diagram_y = (self.HEIGHT - diagram.height) // 2

        # Handle transparency if present
        if diagram.mode == 'RGBA':
            frame.paste(diagram, (diagram_x, diagram_y), diagram)
        else:
            frame.paste(diagram, (diagram_x, diagram_y))

        # Draw CTA at bottom
        bbox = cta_font.getbbox(cta_text)
        cta_width = bbox[2] - bbox[0]
        cta_x = (self.WIDTH - cta_width) // 2
        cta_y = self.HEIGHT - 120
        draw.text((cta_x, cta_y), cta_text, font=cta_font, fill=self.TEXT_COLOR)

        # Save frame
        frame_path = self.temp_dir / f"frame_{uuid.uuid4()}.png"
        frame.save(frame_path)

        return str(frame_path)

    async def build_video(
        self,
        audio_path: str,
        diagram_path: str,
        title: str,
        script_text: str | None = None,
    ) -> str:
        """
        Build a vertical video combining audio, diagram, and text overlay.

        Args:
            audio_path: Path to the TTS audio file
            diagram_path: Path to the diagram image
            title: Video title (shown at top)
            script_text: Optional script text for subtitles

        Returns:
            Path to the generated video file
        """
        # Load audio to get duration
        audio = AudioFileClip(audio_path)
        duration = audio.duration

        # Create frame with text using PIL (no ImageMagick needed)
        frame_path = self._create_frame_with_text(
            diagram_path=diagram_path,
            title=title,
        )

        # Create video from static frame
        video = ImageClip(frame_path).set_duration(duration)

        # Add audio
        video = video.set_audio(audio)

        # Output path
        output_path = self.output_dir / f"{uuid.uuid4()}.mp4"

        # Write video file
        video.write_videofile(
            str(output_path),
            fps=24,  # Lower FPS is fine for static content
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            logger=None,  # Suppress moviepy output
        )

        # Clean up
        audio.close()
        video.close()

        # Clean up temp frame
        try:
            Path(frame_path).unlink()
        except Exception:
            pass

        return str(output_path)

    async def build_video_with_subtitles(
        self,
        audio_path: str,
        diagram_path: str,
        title: str,
        script_text: str,
        words_per_subtitle: int = 5,
    ) -> str:
        """
        Build video with animated subtitles.
        This is a more advanced version that shows text progressively.
        """
        # For the initial version, use the basic build_video
        # Subtitle animation can be added later
        return await self.build_video(
            audio_path=audio_path,
            diagram_path=diagram_path,
            title=title,
            script_text=script_text,
        )


# Singleton instance
video_builder = VideoBuilder()
