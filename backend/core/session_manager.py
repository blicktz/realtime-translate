"""
Session manager for handling session lifecycle, state, and message history.
"""

import uuid
import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
from models import (
    SessionData,
    SessionState,
    SessionSnapshot,
    Message,
    SpeakerTurn,
    LanguageCode,
    SessionMetrics
)
from utils import SessionLogger
from .state_machine import TranslatorStateMachine
from config import settings


class SessionManager:
    """
    Manages all active translation sessions.

    Responsibilities:
    - Create and destroy sessions
    - Track session state and metadata
    - Store message history
    - Monitor session timeouts
    - Provide session metrics
    """

    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}
        self._state_machines: Dict[str, TranslatorStateMachine] = {}
        self._metrics: Dict[str, SessionMetrics] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the session manager and background tasks."""
        # Start cleanup task for inactive sessions
        self._cleanup_task = asyncio.create_task(self._cleanup_inactive_sessions())

    async def stop(self):
        """Stop the session manager and cleanup resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all active sessions
        for session_id in list(self._sessions.keys()):
            await self.close_session(session_id)

    def create_session(
        self,
        home_language: LanguageCode,
        target_language: LanguageCode,
        user_id: Optional[str] = None
    ) -> SessionData:
        """
        Create a new translation session.

        Args:
            home_language: User's native language
            target_language: Language to translate to/from
            user_id: Optional user identifier

        Returns:
            SessionData object with session details
        """
        # Check max sessions limit
        if len(self._sessions) >= settings.max_sessions:
            raise RuntimeError("Maximum number of sessions reached")

        # Generate unique session ID
        session_id = str(uuid.uuid4())

        # Create session data
        session = SessionData(
            session_id=session_id,
            state=SessionState.CONNECTED,
            home_language=home_language,
            target_language=target_language,
            user_id=user_id
        )

        # Create state machine for this session
        state_machine = TranslatorStateMachine(session_id)
        state_machine.set_on_state_change(
            lambda old, new: self._on_state_change(session_id, old, new)
        )
        state_machine.connect()

        # Initialize metrics
        metrics = SessionMetrics(session_id=session_id)

        # Store session
        self._sessions[session_id] = session
        self._state_machines[session_id] = state_machine
        self._metrics[session_id] = metrics

        logger = SessionLogger(session_id)
        logger.info(
            f"Session created: {home_language.value} ↔ {target_language.value}"
        )

        return session

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session by ID."""
        return self._sessions.get(session_id)

    def get_state_machine(self, session_id: str) -> Optional[TranslatorStateMachine]:
        """Get state machine for session."""
        return self._state_machines.get(session_id)

    def get_metrics(self, session_id: str) -> Optional[SessionMetrics]:
        """Get metrics for session."""
        return self._metrics.get(session_id)

    async def close_session(self, session_id: str):
        """Close and cleanup a session."""
        if session_id not in self._sessions:
            return

        # Get state machine and disconnect
        state_machine = self._state_machines.get(session_id)
        if state_machine:
            state_machine.disconnect()

        # Remove from tracking
        session = self._sessions.pop(session_id, None)
        self._state_machines.pop(session_id, None)
        metrics = self._metrics.pop(session_id, None)

        logger = SessionLogger(session_id)
        if session and metrics:
            logger.info(
                f"Session closed - Duration: {self._get_session_duration(session)}s, "
                f"Messages: {len(session.messages)}, "
                f"Avg latency: {metrics.avg_total_latency:.0f}ms"
            )

    def add_message(
        self,
        session_id: str,
        speaker: SpeakerTurn,
        original_text: str,
        translated_text: Optional[str] = None,
        source_language: Optional[LanguageCode] = None,
        target_language: Optional[LanguageCode] = None
    ) -> Optional[Message]:
        """
        Add a message to session history.

        Args:
            session_id: Session identifier
            speaker: Who is speaking (user or partner)
            original_text: Original transcribed text
            translated_text: Translated text
            source_language: Language of original text
            target_language: Language of translation

        Returns:
            Message object if successful, None otherwise
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Determine languages if not provided
        if speaker == SpeakerTurn.USER:
            source_language = source_language or session.home_language
            target_language = target_language or session.target_language
        else:
            source_language = source_language or session.target_language
            target_language = target_language or session.home_language

        # Create message
        message = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            speaker=speaker,
            original_text=original_text,
            translated_text=translated_text,
            source_language=source_language,
            target_language=target_language
        )

        # Add to session history (limited to last 50 messages)
        session.messages.append(message)
        if len(session.messages) > 50:
            session.messages = session.messages[-50:]

        # Update statistics
        if speaker == SpeakerTurn.USER:
            session.total_user_turns += 1
        else:
            session.total_partner_turns += 1

        # Update activity timestamp
        session.last_activity = datetime.utcnow()

        return message

    def update_metrics(
        self,
        session_id: str,
        stt_latency: Optional[float] = None,
        translation_latency: Optional[float] = None,
        tts_latency: Optional[float] = None,
        success: bool = True,
        error_type: Optional[str] = None
    ):
        """Update session metrics with processing latencies."""
        metrics = self._metrics.get(session_id)
        session = self._sessions.get(session_id)

        if not metrics or not session:
            return

        metrics.total_turns += 1

        if success:
            metrics.successful_turns += 1

            # Update latency averages (simple moving average)
            if stt_latency is not None:
                metrics.avg_stt_latency = self._update_average(
                    metrics.avg_stt_latency,
                    stt_latency,
                    metrics.total_turns
                )

            if translation_latency is not None:
                metrics.avg_translation_latency = self._update_average(
                    metrics.avg_translation_latency,
                    translation_latency,
                    metrics.total_turns
                )

            if tts_latency is not None:
                metrics.avg_tts_latency = self._update_average(
                    metrics.avg_tts_latency,
                    tts_latency,
                    metrics.total_turns
                )

            # Calculate total latency
            total = (stt_latency or 0) + (translation_latency or 0) + (tts_latency or 0)
            if total > 0:
                metrics.avg_total_latency = self._update_average(
                    metrics.avg_total_latency,
                    total,
                    metrics.total_turns
                )

                # Update session total processing time
                session.total_processing_time_ms += int(total)

        else:
            metrics.failed_turns += 1

            # Track error types
            if error_type == "stt":
                metrics.stt_errors += 1
            elif error_type == "translation":
                metrics.translation_errors += 1
            elif error_type == "tts":
                metrics.tts_errors += 1

    def list_sessions(self) -> list[SessionSnapshot]:
        """Get a list of all active sessions."""
        snapshots = []
        for session in self._sessions.values():
            snapshot = SessionSnapshot(
                session_id=session.session_id,
                state=session.state,
                home_language=session.home_language,
                target_language=session.target_language,
                created_at=session.created_at,
                last_activity=session.last_activity,
                message_count=len(session.messages)
            )
            snapshots.append(snapshot)

        return snapshots

    async def _cleanup_inactive_sessions(self):
        """Background task to cleanup inactive sessions."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                now = datetime.utcnow()
                timeout_threshold = timedelta(seconds=settings.session_timeout_seconds)

                # Find inactive sessions
                inactive_sessions = []
                for session_id, session in self._sessions.items():
                    if now - session.last_activity > timeout_threshold:
                        inactive_sessions.append(session_id)

                # Close inactive sessions
                for session_id in inactive_sessions:
                    logger = SessionLogger(session_id)
                    logger.info("Closing inactive session (timeout)")
                    await self.close_session(session_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in session cleanup: {e}")

    def _on_state_change(
        self,
        session_id: str,
        old_state: SessionState,
        new_state: SessionState
    ):
        """Callback when session state changes."""
        session = self._sessions.get(session_id)
        if session:
            session.state = new_state
            session.last_activity = datetime.utcnow()

    def _get_session_duration(self, session: SessionData) -> int:
        """Calculate session duration in seconds."""
        duration = datetime.utcnow() - session.created_at
        return int(duration.total_seconds())

    @staticmethod
    def _update_average(current_avg: float, new_value: float, count: int) -> float:
        """Update a running average with a new value."""
        return (current_avg * (count - 1) + new_value) / count


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
