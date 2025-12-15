"""
Message schemas for WebSocket/DataChannel communication.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from .enums import (
    MessageType,
    PTTState,
    SessionState,
    ProcessingStage,
    SpeakerTurn,
    LanguageCode
)


class BaseMessage(BaseModel):
    """Base message structure for all communications."""
    type: MessageType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None


class PTTMessage(BaseMessage):
    """Push-to-Talk state change message from frontend."""
    type: MessageType = MessageType.PTT_STATE
    state: PTTState


class ConnectionStateMessage(BaseMessage):
    """Connection state change message."""
    type: MessageType = MessageType.CONNECTION_STATE
    state: SessionState
    message: Optional[str] = None


class ErrorMessage(BaseMessage):
    """Error message."""
    type: MessageType = MessageType.ERROR
    error_code: str
    error_message: str
    details: Optional[dict] = None


class TranscriptMessage(BaseMessage):
    """Speech transcription message."""
    type: MessageType = MessageType.TRANSCRIPT
    speaker: SpeakerTurn
    text: str
    language: LanguageCode
    confidence: Optional[float] = None
    is_partial: bool = False


class TranslationMessage(BaseMessage):
    """Translation result message to frontend."""
    type: MessageType = MessageType.TRANSLATION
    speaker: SpeakerTurn
    original_text: str
    translated_text: str
    source_language: LanguageCode
    target_language: LanguageCode


class AudioLevelMessage(BaseMessage):
    """Audio level indicator for visualizer."""
    type: MessageType = MessageType.AUDIO_LEVEL
    level: float = Field(ge=0.0, le=1.0)
    speaker: SpeakerTurn


class ThinkingMessage(BaseMessage):
    """Processing indicator message."""
    type: MessageType = MessageType.THINKING
    is_thinking: bool
    stage: ProcessingStage = ProcessingStage.IDLE


class ProcessingStageMessage(BaseMessage):
    """Detailed processing stage update."""
    type: MessageType = MessageType.PROCESSING_STAGE
    stage: ProcessingStage
    speaker: SpeakerTurn


# Session Configuration Messages

class SessionConfig(BaseModel):
    """Session language configuration."""
    session_id: str
    home_language: LanguageCode
    target_language: LanguageCode
    user_id: Optional[str] = None


class SessionCreateRequest(BaseModel):
    """Request to create a new session."""
    home_language: LanguageCode = LanguageCode.ENGLISH
    target_language: LanguageCode = LanguageCode.SPANISH
    user_id: Optional[str] = None


class SessionCreateResponse(BaseModel):
    """Response after session creation."""
    session_id: str
    config: SessionConfig
    webrtc_config: Optional[dict] = None


class WebRTCOffer(BaseModel):
    """WebRTC offer for connection establishment."""
    session_id: str
    sdp: str
    type: str = "offer"


class WebRTCAnswer(BaseModel):
    """WebRTC answer response."""
    session_id: str
    sdp: str
    type: str = "answer"


class ICECandidate(BaseModel):
    """ICE candidate for WebRTC connection."""
    session_id: str
    candidate: str
    sdp_mid: Optional[str] = None
    sdp_m_line_index: Optional[int] = None
