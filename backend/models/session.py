"""
Session data models and management structures.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .enums import SessionState, SpeakerTurn, LanguageCode


class Message(BaseModel):
    """Chat message stored in session history."""
    id: str
    session_id: str
    speaker: SpeakerTurn
    original_text: str
    translated_text: Optional[str] = None
    source_language: LanguageCode
    target_language: Optional[LanguageCode] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    audio_url: Optional[str] = None  # For TTS audio playback


class SessionData(BaseModel):
    """Active session data container."""
    session_id: str
    state: SessionState = SessionState.DISCONNECTED
    home_language: LanguageCode
    target_language: LanguageCode
    user_id: Optional[str] = None

    # Session metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)

    # Current state tracking
    current_speaker: Optional[SpeakerTurn] = None
    is_processing: bool = False

    # Message history (limited to last N messages for memory efficiency)
    messages: List[Message] = Field(default_factory=list, max_length=50)

    # Statistics
    total_user_turns: int = 0
    total_partner_turns: int = 0
    total_processing_time_ms: int = 0


class SessionMetrics(BaseModel):
    """Session performance metrics."""
    session_id: str

    # Latency metrics (milliseconds)
    avg_stt_latency: float = 0.0
    avg_translation_latency: float = 0.0
    avg_tts_latency: float = 0.0
    avg_total_latency: float = 0.0

    # Count metrics
    total_turns: int = 0
    successful_turns: int = 0
    failed_turns: int = 0

    # Error tracking
    stt_errors: int = 0
    translation_errors: int = 0
    tts_errors: int = 0

    # Audio quality
    avg_audio_level: float = 0.0
    silence_detected_count: int = 0


class SessionSnapshot(BaseModel):
    """Lightweight session snapshot for listings."""
    session_id: str
    state: SessionState
    home_language: LanguageCode
    target_language: LanguageCode
    created_at: datetime
    last_activity: datetime
    message_count: int
