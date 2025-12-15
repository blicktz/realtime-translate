"""
Text-to-Speech (TTS) service using OpenAI TTS via Pipecat.
"""

from typing import Optional
from pipecat.services.openai.tts import OpenAITTSService
from pipecat.processors.frame_processor import FrameProcessor
from config import settings, get_tts_voice_for_language
from models import LanguageCode
from utils import get_logger

logger = get_logger(__name__)


class TTSServiceFactory:
    """
    Factory for creating TTS service instances.
    Uses OpenAI TTS API via Pipecat integration.
    """

    @staticmethod
    def create_tts_processor(
        language: LanguageCode,
        voice: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> FrameProcessor:
        """
        Create a TTS processor for a specific language.

        Args:
            language: Language code for speech synthesis
            voice: Voice name (optional, auto-selected based on language)
            session_id: Optional session ID for logging

        Returns:
            Pipecat TTS processor
        """
        try:
            # Auto-select voice based on language if not provided
            if not voice:
                voice = get_tts_voice_for_language(language.value)

            # Create OpenAI TTS service
            tts_service = OpenAITTSService(
                api_key=settings.openai_api_key,
                model=settings.openai_tts_model,
                voice=voice,
            )

            log_context = f"session={session_id}" if session_id else "global"
            logger.info(
                f"TTS service created: language={language.value}, "
                f"voice={voice}, model={settings.openai_tts_model} ({log_context})"
            )

            return tts_service

        except Exception as e:
            logger.error(f"Failed to create TTS service: {e}")
            raise


class AdaptiveTTSService:
    """
    Adaptive TTS service that can switch languages and voices dynamically.
    """

    def __init__(self):
        self._current_language: Optional[LanguageCode] = None
        self._current_voice: Optional[str] = None
        self._tts_processor: Optional[FrameProcessor] = None

    def set_language(
        self,
        language: LanguageCode,
        voice: Optional[str] = None
    ):
        """
        Set or change the target language and voice for TTS.

        Args:
            language: New language code
            voice: Voice name (optional)
        """
        # Auto-select voice if not provided
        if not voice:
            voice = get_tts_voice_for_language(language.value)

        # Recreate processor if settings changed
        if language != self._current_language or voice != self._current_voice:
            self._current_language = language
            self._current_voice = voice
            self._tts_processor = TTSServiceFactory.create_tts_processor(
                language,
                voice
            )
            logger.debug(
                f"TTS settings updated: language={language.value}, voice={voice}"
            )

    def get_processor(
        self,
        language: LanguageCode,
        voice: Optional[str] = None
    ) -> FrameProcessor:
        """
        Get TTS processor for a specific language and voice.

        Args:
            language: Language code
            voice: Voice name (optional)

        Returns:
            TTS processor
        """
        # Recreate processor if language/voice changed
        if not voice:
            voice = get_tts_voice_for_language(language.value)

        if (language != self._current_language or
            voice != self._current_voice or
            not self._tts_processor):
            self.set_language(language, voice)

        return self._tts_processor


# Voice configuration

AVAILABLE_VOICES = {
    "alloy": "Neutral, balanced voice",
    "echo": "Male, clear and expressive",
    "fable": "British accent, storytelling quality",
    "onyx": "Deep male voice",
    "nova": "Female, friendly and energetic",
    "shimmer": "Soft female voice",
}


def list_available_voices() -> dict:
    """Get list of available TTS voices."""
    return AVAILABLE_VOICES


def get_tts_config() -> dict:
    """Get TTS service configuration."""
    return {
        "model": settings.openai_tts_model,
        "default_voice": settings.openai_tts_voice,
        "api_key": settings.openai_api_key[:10] + "..." if settings.openai_api_key else "NOT_SET",
        "timeout": settings.tts_timeout_seconds,
        "available_voices": list(AVAILABLE_VOICES.keys()),
    }


def validate_tts_config():
    """Validate TTS configuration."""
    if not settings.openai_api_key:
        raise ValueError("OpenAI API key not configured")

    if settings.openai_tts_voice not in AVAILABLE_VOICES:
        logger.warning(
            f"Configured voice '{settings.openai_tts_voice}' not in known voices list"
        )

    logger.info(
        f"TTS configuration validated: model={settings.openai_tts_model}, "
        f"voice={settings.openai_tts_voice}"
    )
