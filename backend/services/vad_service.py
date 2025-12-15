"""
Voice Activity Detection (VAD) service using Silero VAD via Pipecat.
"""

from typing import Optional
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.processors.frame_processor import FrameProcessor
from config import settings
from utils import get_logger

logger = get_logger(__name__)


class VADServiceFactory:
    """
    Factory for creating VAD (Voice Activity Detection) processors.
    Uses Silero VAD via Pipecat integration.
    """

    @staticmethod
    def create_vad_processor(
        confidence_threshold: Optional[float] = None,
        start_secs: Optional[float] = None,
        stop_secs: Optional[float] = None,
        session_id: Optional[str] = None
    ) -> FrameProcessor:
        """
        Create a VAD processor with Silero.

        Args:
            confidence_threshold: Confidence threshold for speech detection (0.0-1.0)
            start_secs: Seconds of speech before triggering start
            stop_secs: Seconds of silence before triggering stop
            session_id: Optional session ID for logging

        Returns:
            Pipecat VAD processor
        """
        try:
            # Use configured values or defaults
            confidence = confidence_threshold or settings.vad_confidence_threshold
            start = start_secs or settings.vad_start_secs
            stop = stop_secs or settings.vad_stop_secs

            # Create VAD parameters
            vad_params = VADParams(
                confidence=confidence,
                start_secs=start,
                stop_secs=stop,
            )

            # Create Silero VAD analyzer
            vad_analyzer = SileroVADAnalyzer(params=vad_params)

            log_context = f"session={session_id}" if session_id else "global"
            logger.info(
                f"VAD analyzer created: confidence={confidence}, "
                f"start={start}s, stop={stop}s ({log_context})"
            )

            return vad_analyzer

        except Exception as e:
            logger.error(f"Failed to create VAD analyzer: {e}")
            raise


class DynamicVADService:
    """
    Dynamic VAD service that can be enabled/disabled based on PTT state.

    In Nebula Translate:
    - VAD is DISABLED when PTT is pressed (user speaking)
    - VAD is ENABLED when PTT is released (partner speaking)
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id
        self._vad_processor: Optional[FrameProcessor] = None
        self._is_enabled = False

        # Create VAD processor (but it will only be active when enabled)
        self._vad_processor = VADServiceFactory.create_vad_processor(
            session_id=session_id
        )

    def enable(self):
        """Enable VAD for partner speech detection."""
        self._is_enabled = True
        logger.debug(f"VAD enabled (session={self.session_id})")

    def disable(self):
        """Disable VAD (user is speaking)."""
        self._is_enabled = False
        logger.debug(f"VAD disabled (session={self.session_id})")

    @property
    def is_enabled(self) -> bool:
        """Check if VAD is currently enabled."""
        return self._is_enabled

    def get_processor(self) -> FrameProcessor:
        """Get the VAD processor."""
        return self._vad_processor


# Configuration helpers

def get_vad_config() -> dict:
    """Get VAD service configuration."""
    return {
        "confidence_threshold": settings.vad_confidence_threshold,
        "start_secs": settings.vad_start_secs,
        "stop_secs": settings.vad_stop_secs,
    }


def validate_vad_config():
    """Validate VAD configuration."""
    if not (0.0 <= settings.vad_confidence_threshold <= 1.0):
        raise ValueError(
            f"VAD confidence threshold must be between 0.0 and 1.0, "
            f"got {settings.vad_confidence_threshold}"
        )

    if settings.vad_start_secs < 0.1:
        logger.warning(
            f"VAD start_secs is very low ({settings.vad_start_secs}), "
            "may cause false positives"
        )

    if settings.vad_stop_secs < 0.5:
        logger.warning(
            f"VAD stop_secs is very low ({settings.vad_stop_secs}), "
            "may cut off speech prematurely"
        )

    logger.info(
        f"VAD configuration validated: confidence={settings.vad_confidence_threshold}, "
        f"start={settings.vad_start_secs}s, stop={settings.vad_stop_secs}s"
    )


# VAD parameter recommendations based on use case

VAD_PRESETS = {
    "aggressive": {
        "confidence_threshold": 0.8,
        "start_secs": 0.1,
        "stop_secs": 0.5,
        "description": "Quick response, may have false positives"
    },
    "balanced": {
        "confidence_threshold": 0.7,
        "start_secs": 0.2,
        "stop_secs": 0.8,
        "description": "Default settings, good for most cases"
    },
    "conservative": {
        "confidence_threshold": 0.6,
        "start_secs": 0.3,
        "stop_secs": 1.0,
        "description": "Fewer false positives, slower response"
    },
    "quiet_environment": {
        "confidence_threshold": 0.5,
        "start_secs": 0.2,
        "stop_secs": 0.7,
        "description": "Optimized for low background noise"
    },
    "noisy_environment": {
        "confidence_threshold": 0.85,
        "start_secs": 0.3,
        "stop_secs": 1.2,
        "description": "Optimized for high background noise"
    }
}


def get_vad_preset(preset_name: str) -> dict:
    """
    Get VAD configuration preset.

    Args:
        preset_name: One of 'aggressive', 'balanced', 'conservative',
                     'quiet_environment', 'noisy_environment'

    Returns:
        Dictionary with VAD parameters
    """
    if preset_name not in VAD_PRESETS:
        raise ValueError(f"Unknown VAD preset: {preset_name}")

    return VAD_PRESETS[preset_name]


def list_vad_presets() -> dict:
    """List all available VAD presets."""
    return VAD_PRESETS
