"""
State machine for managing PTT-based translation workflow.

The state machine enforces the strict PTT logic from the PRD:
- User Turn (PTT Pressed): User speaks → Audio output in target language
- Partner Turn (PTT Released): Partner speaks → Text output in home language
"""

from typing import Optional, Callable
from models import SessionState, PTTState, SpeakerTurn
from utils import SessionLogger


class TranslatorStateMachine:
    """
    Manages session state transitions based on PTT input and processing stages.

    State Transitions:
    DISCONNECTED → CONNECTED (on connection establish)
    CONNECTED → USER_SPEAKING (on PTT press)
    USER_SPEAKING → USER_PROCESSING (on speech end/PTT release while processing)
    USER_PROCESSING → CONNECTED or PARTNER_LISTENING (on processing complete)
    CONNECTED/PARTNER_LISTENING → PARTNER_PROCESSING (on VAD speech detected)
    PARTNER_PROCESSING → PARTNER_LISTENING (on processing complete)
    ANY → ERROR (on critical failure)
    ANY → DISCONNECTED (on disconnect)
    """

    def __init__(self, session_id: str, logger: Optional[SessionLogger] = None):
        self.session_id = session_id
        self.logger = logger or SessionLogger(session_id)
        self._state = SessionState.DISCONNECTED
        self._ptt_pressed = False
        self._is_processing = False
        self._current_speaker: Optional[SpeakerTurn] = None

        # State change callbacks
        self._on_state_change: Optional[Callable[[SessionState, SessionState], None]] = None

    @property
    def state(self) -> SessionState:
        """Get current state."""
        return self._state

    @property
    def current_speaker(self) -> Optional[SpeakerTurn]:
        """Get current speaker (user or partner)."""
        return self._current_speaker

    @property
    def is_user_turn(self) -> bool:
        """Check if it's currently user's turn to speak."""
        return self._ptt_pressed

    @property
    def is_partner_turn(self) -> bool:
        """Check if it's currently partner's turn to speak."""
        return not self._ptt_pressed and self._state in [
            SessionState.PARTNER_LISTENING,
            SessionState.PARTNER_PROCESSING
        ]

    @property
    def should_enable_vad(self) -> bool:
        """Determine if VAD should be active."""
        # VAD only active during partner's turn (PTT released)
        return not self._ptt_pressed and self._state in [
            SessionState.CONNECTED,
            SessionState.PARTNER_LISTENING
        ]

    @property
    def should_output_audio(self) -> bool:
        """Determine if TTS audio should be played."""
        # Audio output only during user's turn
        return self._state in [SessionState.USER_SPEAKING, SessionState.USER_PROCESSING]

    def set_on_state_change(self, callback: Callable[[SessionState, SessionState], None]):
        """Set callback for state changes."""
        self._on_state_change = callback

    def connect(self):
        """Transition to connected state."""
        self._transition_to(SessionState.CONNECTED)
        self.logger.info("Session connected")

    def disconnect(self):
        """Transition to disconnected state."""
        self._transition_to(SessionState.DISCONNECTED)
        self._ptt_pressed = False
        self._is_processing = False
        self._current_speaker = None
        self.logger.info("Session disconnected")

    def handle_ptt_press(self):
        """
        Handle PTT button press event.
        Forces transition to USER_SPEAKING state (strict PTT override).
        """
        if self._state == SessionState.DISCONNECTED:
            self.logger.warning("PTT press ignored: session not connected")
            return

        self._ptt_pressed = True
        self._current_speaker = SpeakerTurn.USER

        # PTT press ALWAYS forces user turn, regardless of current state
        if self._state != SessionState.USER_SPEAKING:
            self._transition_to(SessionState.USER_SPEAKING)
            self.logger.info("PTT pressed → User turn started")

    def handle_ptt_release(self):
        """
        Handle PTT button release event.
        Transitions to partner listening mode.
        """
        if self._state == SessionState.DISCONNECTED:
            return

        self._ptt_pressed = False

        # If user was speaking and processing is ongoing, move to USER_PROCESSING
        if self._state == SessionState.USER_SPEAKING:
            if self._is_processing:
                self._transition_to(SessionState.USER_PROCESSING)
                self.logger.info("PTT released → User processing")
            else:
                self._transition_to(SessionState.PARTNER_LISTENING)
                self._current_speaker = None
                self.logger.info("PTT released → Partner listening mode")

    def start_user_processing(self):
        """Mark that user speech processing has started."""
        self._is_processing = True

        if self._ptt_pressed:
            # User still holding PTT
            self._state = SessionState.USER_SPEAKING
        else:
            # User released PTT, now processing
            self._transition_to(SessionState.USER_PROCESSING)

        self.logger.debug("User speech processing started")

    def finish_user_processing(self):
        """Mark that user speech processing has completed."""
        self._is_processing = False
        self._current_speaker = None

        # Transition to partner listening mode
        if self._state in [SessionState.USER_SPEAKING, SessionState.USER_PROCESSING]:
            self._transition_to(SessionState.PARTNER_LISTENING)
            self.logger.debug("User processing complete → Partner listening")

    def start_partner_processing(self):
        """Mark that partner speech has been detected and processing started."""
        if not self._ptt_pressed and self.should_enable_vad:
            self._is_processing = True
            self._current_speaker = SpeakerTurn.PARTNER
            self._transition_to(SessionState.PARTNER_PROCESSING)
            self.logger.info("Partner speech detected → Partner processing")

    def finish_partner_processing(self):
        """Mark that partner speech processing has completed."""
        self._is_processing = False
        self._current_speaker = None

        # Return to listening mode
        if self._state == SessionState.PARTNER_PROCESSING:
            self._transition_to(SessionState.PARTNER_LISTENING)
            self.logger.debug("Partner processing complete → Listening")

    def handle_error(self, error_message: str):
        """Transition to error state."""
        self.logger.error(f"State machine error: {error_message}")
        self._transition_to(SessionState.ERROR)
        self._is_processing = False

    def _transition_to(self, new_state: SessionState):
        """Internal method to transition to a new state."""
        if new_state == self._state:
            return

        old_state = self._state
        self._state = new_state

        self.logger.debug(f"State transition: {old_state.value} → {new_state.value}")

        # Invoke callback if registered
        if self._on_state_change:
            self._on_state_change(old_state, new_state)

    def reset(self):
        """Reset state machine to initial state."""
        self._state = SessionState.CONNECTED
        self._ptt_pressed = False
        self._is_processing = False
        self._current_speaker = None
        self.logger.info("State machine reset")

    def get_state_info(self) -> dict:
        """Get current state information for debugging."""
        return {
            "state": self._state.value,
            "ptt_pressed": self._ptt_pressed,
            "is_processing": self._is_processing,
            "current_speaker": self._current_speaker.value if self._current_speaker else None,
            "should_enable_vad": self.should_enable_vad,
            "should_output_audio": self.should_output_audio,
        }
