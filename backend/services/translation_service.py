"""
Translation service using OpenRouter LLM APIs.

Uses LLMs (GPT-4, Claude, etc.) via OpenRouter for high-quality,
context-aware translation that preserves tone and nuance.
"""

import asyncio
import httpx
from typing import Optional, List
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import Frame, TextFrame, TranscriptionFrame
from config import settings
from models import LanguageCode, LANGUAGE_NAMES
from utils import get_logger

logger = get_logger(__name__)


class TranslationProcessor(FrameProcessor):
    """
    Custom Pipecat processor for LLM-based translation.

    Receives text frames from STT, translates them, and outputs translated text frames.
    """

    def __init__(
        self,
        source_language: LanguageCode,
        target_language: LanguageCode,
        model: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        super().__init__()
        self.source_language = source_language
        self.target_language = target_language
        self.model = model or settings.openrouter_model
        self.session_id = session_id

        # HTTP client for API calls
        self.client = httpx.AsyncClient(
            timeout=settings.translation_timeout_seconds
        )

        # System prompt for translation
        self.system_prompt = self._create_system_prompt()

        logger.info(
            f"Translation processor created: {source_language.value} → "
            f"{target_language.value}, model={self.model}"
        )

    def _create_system_prompt(self) -> str:
        """Create system prompt for translation model."""
        source_name = LANGUAGE_NAMES.get(self.source_language, self.source_language.value)
        target_name = LANGUAGE_NAMES.get(self.target_language, self.target_language.value)

        return f"""You are a professional translator specializing in real-time conversation translation.

Your task is to translate from {source_name} to {target_name}.

Guidelines:
1. Translate the EXACT meaning, preserving tone, formality, and nuance
2. For informal speech, use informal target language; for formal speech, use formal target language
3. Preserve emotional content (excitement, frustration, humor, etc.)
4. Keep cultural context when possible, but adapt idioms for clarity
5. Output ONLY the translation, no explanations or notes
6. For very short utterances (1-2 words), provide natural equivalent
7. If the input is unclear or broken, provide the best possible translation
8. Maintain consistency with conversation context

Output format: Plain text translation only, no markdown or formatting."""

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process text frames for translation."""

        # Handle non-text frames (forward without logging to reduce noise)
        if not isinstance(frame, (TextFrame, TranscriptionFrame)):
            await super().process_frame(frame, direction)
            await self.push_frame(frame, direction)
            return

        # Only process downstream text frames
        if direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return

        # Translate the text
        try:
            original_text = frame.text

            if not original_text or not original_text.strip():
                # Empty text, skip translation
                await self.push_frame(frame, direction)
                return

            logger.info(f"[TRANSLATION] Translating: '{original_text}'")

            # Call translation API
            translated_text = await self._translate(original_text)

            logger.info(f"[TRANSLATION] ✅ Translation complete: '{translated_text}'")

            # Create new text frame with translation
            translated_frame = TextFrame(text=translated_text)

            # Push translated frame downstream
            await self.push_frame(translated_frame, direction)

        except Exception as e:
            logger.error(f"[TRANSLATION] ❌ Translation error: {e}", exc_info=True)

            # On error, pass through original text
            await self.push_frame(frame, direction)

    async def _translate(self, text: str) -> str:
        """
        Translate text using OpenRouter API.

        Args:
            text: Source text to translate

        Returns:
            Translated text
        """
        try:
            # Prepare API request
            headers = {
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": "https://nebula-translate.app",  # Optional: your app URL
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": text}
                ],
                "max_tokens": 500,  # Generous limit for translations
                "temperature": 0.3,  # Lower temperature for more consistent translations
            }

            # Make API call
            response = await self.client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                json=payload,
                headers=headers
            )

            response.raise_for_status()

            # Parse response
            result = response.json()
            translated_text = result["choices"][0]["message"]["content"].strip()

            return translated_text

        except httpx.HTTPError as e:
            logger.error(f"OpenRouter API error: {e}")

            # Try fallback model
            if self.model != settings.openrouter_fallback_models[0]:
                logger.info("Trying fallback model...")
                fallback_model = settings.openrouter_fallback_models[0]
                return await self._translate_with_model(text, fallback_model)

            raise

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise

    async def _translate_with_model(self, text: str, model: str) -> str:
        """Translate with a specific model (for fallback)."""
        original_model = self.model
        self.model = model

        try:
            result = await self._translate(text)
            return result
        finally:
            self.model = original_model

    async def cleanup(self):
        """Cleanup resources."""
        await self.client.aclose()


class TranslationServiceFactory:
    """
    Factory for creating translation processors.
    """

    @staticmethod
    def create_translation_processor(
        source_language: LanguageCode,
        target_language: LanguageCode,
        model: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> TranslationProcessor:
        """
        Create a translation processor.

        Args:
            source_language: Source language code
            target_language: Target language code
            model: LLM model to use (optional)
            session_id: Session ID for logging (optional)

        Returns:
            Translation processor
        """
        return TranslationProcessor(
            source_language=source_language,
            target_language=target_language,
            model=model,
            session_id=session_id
        )


# Configuration helpers

def get_translation_config() -> dict:
    """Get translation service configuration."""
    return {
        "base_url": settings.openrouter_base_url,
        "default_model": settings.openrouter_model,
        "fallback_models": settings.openrouter_fallback_models,
        "api_key": settings.openrouter_api_key[:10] + "..." if settings.openrouter_api_key else "NOT_SET",
        "timeout": settings.translation_timeout_seconds,
    }


def validate_translation_config():
    """Validate translation configuration."""
    if not settings.openrouter_api_key:
        raise ValueError("OpenRouter API key not configured")

    logger.info(
        f"Translation configuration validated: model={settings.openrouter_model}, "
        f"fallbacks={settings.openrouter_fallback_models}"
    )


# Supported model list (for reference)
SUPPORTED_MODELS = {
    "anthropic/claude-3.5-sonnet": "Best quality, slower",
    "anthropic/claude-3-opus": "High quality, balanced",
    "openai/gpt-4-turbo-preview": "Fast, high quality",
    "openai/gpt-4": "Reliable, good quality",
    "openai/gpt-3.5-turbo": "Fast, lower cost",
}


def list_supported_models() -> dict:
    """Get list of supported translation models."""
    return SUPPORTED_MODELS
