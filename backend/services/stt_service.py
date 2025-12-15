"""
Speech-to-Text (STT) service using OpenAI Whisper via Pipecat.
"""

from typing import Optional
from pipecat.services.openai.stt import OpenAISTTService
from pipecat.processors.frame_processor import FrameProcessor
from config import settings, Settings
from models import LanguageCode
from utils import get_logger

logger = get_logger(__name__)


class STTServiceFactory:
    """
    Factory for creating STT service instances.
    Uses OpenAI Whisper API via Pipecat integration.
    """

    @staticmethod
    def create_stt_processor(
        language: LanguageCode,
        session_id: Optional[str] = None
    ) -> FrameProcessor:
        """
        Create an STT processor for a specific language.

        Args:
            language: Language code for transcription
            session_id: Optional session ID for logging

        Returns:
            Pipecat STT processor
        """
        try:
            # Create OpenAI STT service
            stt_service = OpenAISTTService(
                api_key=settings.openai_api_key,
                model=settings.openai_stt_model,
                language=language.value,  # Language hint for better accuracy
            )

            log_context = f"session={session_id}" if session_id else "global"
            logger.info(
                f"STT service created for language: {language.value} ({log_context})"
            )

            return stt_service

        except Exception as e:
            logger.error(f"Failed to create STT service: {e}")
            raise


class AdaptiveSTTService:
    """
    Adaptive STT service that can switch languages dynamically.
    Useful for sessions where language detection might be needed.
    """

    def __init__(self):
        self._current_language: Optional[LanguageCode] = None
        self._stt_processor: Optional[FrameProcessor] = None

    def set_language(self, language: LanguageCode):
        """
        Set or change the target language for transcription.

        Args:
            language: New language code
        """
        if language != self._current_language:
            self._current_language = language
            self._stt_processor = STTServiceFactory.create_stt_processor(language)
            logger.debug(f"STT language switched to: {language.value}")

    def get_processor(self, language: LanguageCode) -> FrameProcessor:
        """
        Get STT processor for a specific language.

        Args:
            language: Language code

        Returns:
            STT processor
        """
        # Recreate processor if language changed
        if language != self._current_language or not self._stt_processor:
            self.set_language(language)

        return self._stt_processor


# Configuration helpers

def get_stt_config() -> dict:
    """Get STT service configuration."""
    return {
        "model": settings.openai_stt_model,
        "api_key": settings.openai_api_key[:10] + "..." if settings.openai_api_key else "NOT_SET",
        "timeout": settings.stt_timeout_seconds,
    }


def validate_stt_config():
    """Validate STT configuration."""
    if not settings.openai_api_key:
        raise ValueError("OpenAI API key not configured")

    logger.info(f"STT configuration validated: model={settings.openai_stt_model}")
