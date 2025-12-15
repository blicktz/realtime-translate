"""
Configuration management for Nebula Translate backend.
Loads environment variables and provides typed configuration access.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BeforeValidator
from typing import Optional, List, Annotated
from enum import Enum


def parse_comma_separated(v):
    """Parse comma-separated string into list."""
    if isinstance(v, str):
        return [item.strip() for item in v.split(',') if item.strip()]
    return v


class Environment(str, Enum):
    """Deployment environment types."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class TransportMode(str, Enum):
    """Transport layer modes."""
    WEBSOCKET = "websocket"  # Development/testing
    WEBRTC = "webrtc"        # Production


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Environment
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    log_level: str = "INFO"

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: Annotated[List[str], BeforeValidator(parse_comma_separated)] = [
        "http://localhost:3000",
        "http://localhost:3001"
    ]

    # Transport Configuration
    transport_mode: TransportMode = TransportMode.WEBSOCKET

    # OpenAI Configuration
    openai_api_key: str
    openai_stt_model: str = "whisper-1"
    openai_tts_model: str = "tts-1"
    openai_tts_voice: str = "alloy"  # Default voice, can be changed per language

    # OpenRouter Configuration (for LLM translation)
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "anthropic/claude-3.5-sonnet"  # Default translation model
    openrouter_fallback_models: List[str] = [
        "openai/gpt-4-turbo-preview",
        "anthropic/claude-3-opus"
    ]

    # WebRTC Configuration
    stun_server_url: str = "stun:stun.l.google.com:19302"
    turn_server_url: Optional[str] = None
    turn_username: Optional[str] = None
    turn_credential: Optional[str] = None

    # VAD (Voice Activity Detection) Configuration
    vad_confidence_threshold: float = 0.7
    vad_start_secs: float = 0.2
    vad_stop_secs: float = 0.8

    # Audio Configuration
    audio_sample_rate: int = 16000
    audio_channels: int = 1

    # Session Configuration
    session_timeout_seconds: int = 300  # 5 minutes of inactivity
    max_sessions: int = 100

    # Processing Timeouts
    stt_timeout_seconds: int = 10
    translation_timeout_seconds: int = 15
    tts_timeout_seconds: int = 10

    # Rate Limiting
    max_requests_per_minute: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()


def get_webrtc_config() -> dict:
    """Get WebRTC ICE server configuration."""
    ice_servers = [
        {"urls": [settings.stun_server_url]}
    ]

    if settings.turn_server_url:
        ice_servers.append({
            "urls": [settings.turn_server_url],
            "username": settings.turn_username,
            "credential": settings.turn_credential
        })

    return {
        "iceServers": ice_servers,
        "iceTransportPolicy": "all",
        "bundlePolicy": "max-bundle",
        "rtcpMuxPolicy": "require"
    }


def get_tts_voice_for_language(language_code: str) -> str:
    """Map language codes to appropriate TTS voices."""
    voice_map = {
        "en": "alloy",
        "es": "nova",
        "fr": "shimmer",
        "de": "echo",
        "it": "fable",
        "pt": "onyx",
        "ja": "nova",
        "ko": "shimmer",
        "zh": "alloy",
    }

    # Extract language prefix (e.g., "en-US" -> "en")
    lang_prefix = language_code.split("-")[0].lower()
    return voice_map.get(lang_prefix, settings.openai_tts_voice)
