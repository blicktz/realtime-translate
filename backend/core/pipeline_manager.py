"""
Pipecat Pipeline Manager for Nebula Translate.

Orchestrates the frame-based audio processing pipeline:
- User Turn: Audio Input → STT → Translation → TTS → Audio Output
- Partner Turn: Audio Input → VAD → STT → Translation → Text Output (no TTS)
"""

import asyncio
from typing import Optional, Callable, Any
from datetime import datetime

# Pipecat imports
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.frames.frames import (
    Frame,
    AudioRawFrame,
    TextFrame,
    StartFrame,
    EndFrame,
    CancelFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame
)

from models import SessionData, SpeakerTurn, PTTState
from utils import SessionLogger, calculate_audio_level
from .state_machine import TranslatorStateMachine


class PipelineManager:
    """
    Manages Pipecat pipeline for a single session.

    The pipeline dynamically routes frames based on PTT state:
    - PTT Pressed: User pipeline (with TTS output)
    - PTT Released: Partner pipeline (text only, VAD enabled)
    """

    def __init__(
        self,
        session: SessionData,
        state_machine: TranslatorStateMachine,
        logger: Optional[SessionLogger] = None
    ):
        self.session = session
        self.state_machine = state_machine
        self.logger = logger or SessionLogger(session.session_id)

        self.pipeline: Optional[Pipeline] = None
        self.task: Optional[PipelineTask] = None
        self.runner: Optional[PipelineRunner] = None

        # Service processors (will be initialized when services are created)
        self.stt_processor: Optional[FrameProcessor] = None
        self.tts_processor: Optional[FrameProcessor] = None
        self.translation_processor: Optional[FrameProcessor] = None
        self.vad_processor: Optional[FrameProcessor] = None

        # Callbacks for sending data to frontend
        self.on_audio_output: Optional[Callable[[bytes], None]] = None
        self.on_text_output: Optional[Callable[[str, SpeakerTurn], None]] = None
        self.on_audio_level: Optional[Callable[[float, SpeakerTurn], None]] = None
        self.on_thinking: Optional[Callable[[bool], None]] = None

        # Processing tracking
        self._processing_start_time: Optional[datetime] = None
        self._stt_start_time: Optional[datetime] = None
        self._translation_start_time: Optional[datetime] = None
        self._tts_start_time: Optional[datetime] = None

    def set_services(
        self,
        stt_processor: FrameProcessor,
        tts_processor: FrameProcessor,
        translation_processor: FrameProcessor,
        vad_processor: Optional[FrameProcessor] = None
    ):
        """Set the service processors from the services module.

        Note: vad_processor is kept for backwards compatibility but is not used in the pipeline.
        Speech routing is controlled by PTT state via AudioRouterProcessor.
        """
        self.stt_processor = stt_processor
        self.tts_processor = tts_processor
        self.translation_processor = translation_processor
        self.vad_processor = vad_processor

    async def initialize(self):
        """Initialize the Pipecat pipeline."""
        if not all([
            self.stt_processor,
            self.tts_processor,
            self.translation_processor,
            self.vad_processor  # VAD is now required
        ]):
            raise RuntimeError("Services must be set before initializing pipeline")

        # Create custom processors for routing and callbacks
        audio_router = AudioRouterProcessor(self)
        text_router = TextRouterProcessor(self)
        audio_level_monitor = AudioLevelMonitor(self)

        # Build the pipeline
        # VAD -> AudioRouter -> STT
        self.pipeline = Pipeline([
            audio_level_monitor,    # Monitor input audio levels
            self.vad_processor,     # VAD (generates Speaking frames)
            audio_router,           # Route/Filter based on PTT state
            self.stt_processor,     # Speech-to-text
            self.translation_processor,  # Translation
            text_router,            # Route text based on state
            self.tts_processor,     # Text-to-speech (only for user turn)
        ])

        self.logger.info("Pipecat pipeline initialized")

    async def start(self):
        """Start the pipeline processing."""
        if not self.pipeline:
            raise RuntimeError("Pipeline must be initialized before starting")

        self.task = PipelineTask(self.pipeline)
        self.runner = PipelineRunner()

        await self.runner.run(self.task)
        self.logger.info("Pipeline started")

    async def stop(self):
        """Stop the pipeline processing."""
        if self.task:
            await self.task.cancel()

        if self.runner:
            await self.runner.stop()

        self.logger.info("Pipeline stopped")

    async def process_audio_input(self, audio_data: bytes):
        """
        Process incoming audio data from microphone.

        Args:
            audio_data: Raw PCM16 audio bytes
        """
        if not self.pipeline or not self.task:
            return

        # Create audio frame
        audio_frame = AudioRawFrame(
            audio=audio_data,
            sample_rate=16000,
            num_channels=1
        )

        # Push frame into pipeline
        await self.task.queue_frame(audio_frame, FrameDirection.DOWNSTREAM)

    async def handle_ptt_press(self):
        """Handle PTT button press event."""
        self.state_machine.handle_ptt_press()
        self.logger.debug("PTT pressed - User turn started")

        # Reset processing timers
        self._processing_start_time = datetime.utcnow()

    async def handle_ptt_release(self):
        """Handle PTT button release event."""
        self.state_machine.handle_ptt_release()
        self.logger.debug("PTT released - Partner listening mode")

    def start_processing(self, stage: str):
        """Mark the start of a processing stage."""
        now = datetime.utcnow()

        if stage == "stt":
            self._stt_start_time = now
        elif stage == "translation":
            self._translation_start_time = now
        elif stage == "tts":
            self._tts_start_time = now

        # Notify frontend that processing started
        if self.on_thinking:
            self.on_thinking(True)

    def finish_processing(self, stage: str) -> float:
        """
        Mark the end of a processing stage and return latency.

        Args:
            stage: Processing stage name (stt, translation, tts)

        Returns:
            Latency in milliseconds
        """
        now = datetime.utcnow()
        latency_ms = 0.0

        if stage == "stt" and self._stt_start_time:
            latency_ms = (now - self._stt_start_time).total_seconds() * 1000
            self._stt_start_time = None

        elif stage == "translation" and self._translation_start_time:
            latency_ms = (now - self._translation_start_time).total_seconds() * 1000
            self._translation_start_time = None

        elif stage == "tts" and self._tts_start_time:
            latency_ms = (now - self._tts_start_time).total_seconds() * 1000
            self._tts_start_time = None

        return latency_ms

    def _emit_audio_output(self, audio_data: bytes):
        """Emit audio output to frontend."""
        if self.on_audio_output:
            self.on_audio_output(audio_data)

    def _emit_text_output(self, text: str, speaker: SpeakerTurn):
        """Emit text output to frontend."""
        if self.on_text_output:
            self.on_text_output(text, speaker)

    def _emit_audio_level(self, level: float, speaker: SpeakerTurn):
        """Emit audio level for visualization."""
        if self.on_audio_level:
            self.on_audio_level(level, speaker)


class AudioRouterProcessor(FrameProcessor):
    """
    Routes audio frames based on PTT state.

    - PTT Pressed: Forward to STT (user pipeline)
    - PTT Released + VAD active: Forward to STT (partner pipeline)
    - PTT Released + No VAD: Drop frames
    """

    def __init__(self, manager: PipelineManager):
        super().__init__()
        self.manager = manager
        self._frame_count = 0
        self._last_log_time = None

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        # Handle system frames (StartFrame, EndFrame, etc.) with parent class
        if not isinstance(frame, (AudioRawFrame, UserStartedSpeakingFrame, UserStoppedSpeakingFrame,
                                   VADUserStartedSpeakingFrame, VADUserStoppedSpeakingFrame)):
            await super().process_frame(frame, direction)
            return

        # Only process downstream frames
        if direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return

        # Handle Speaking Frames (VAD or PTT) - transport generates VAD* versions
        if isinstance(frame, (UserStartedSpeakingFrame, VADUserStartedSpeakingFrame)):
            # Always pass StartSpeaking (PTT or VAD)
            state_info = self.manager.state_machine.get_state_info()
            self.manager.logger.info(
                f"[AUDIO_ROUTER] 🎤 UserStartedSpeakingFrame received - "
                f"State: {state_info['state']}, PTT: {state_info['ptt_pressed']}"
            )
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, (UserStoppedSpeakingFrame, VADUserStoppedSpeakingFrame)):
            # If PTT is pressed, IGNORE StopSpeaking (prevent VAD from cutting off user)
            if self.manager.state_machine.is_user_turn:
                self.manager.logger.info(
                    "[AUDIO_ROUTER] 🔇 Ignoring UserStoppedSpeakingFrame (PTT pressed, user still speaking)"
                )
                return
            # Otherwise pass it
            state_info = self.manager.state_machine.get_state_info()
            self.manager.logger.info(
                f"[AUDIO_ROUTER] 🔇 UserStoppedSpeakingFrame received - "
                f"State: {state_info['state']}, PTT: {state_info['ptt_pressed']}"
            )
            await self.push_frame(frame, direction)
            return

        # Handle Audio Frames
        if isinstance(frame, AudioRawFrame):
            # Log audio frame receipt (throttled)
            self._frame_count += 1

            # Log every 50th frame with routing decision (more frequent for debugging)
            if self._frame_count % 50 == 1:
                state_info = self.manager.state_machine.get_state_info()
                self.manager.logger.info(
                    f"[AUDIO_ROUTER] Frame #{self._frame_count} - State: {state_info['state']}, "
                    f"PTT: {state_info['ptt_pressed']}, VAD_should_enable: {state_info['should_enable_vad']}"
                )

            # Route audio based on state
            if self.manager.state_machine.is_user_turn:
                # User turn: Forward audio (PTT pressed)
                if self._frame_count % 50 == 1:
                    self.manager.logger.info(f"[AUDIO_ROUTER] ✅ Forwarding frame #{self._frame_count} (USER TURN)")
                await self.push_frame(frame, direction)

            elif self.manager.state_machine.should_enable_vad:
                # Partner turn: Forward audio (VAD enabled)
                if self._frame_count % 50 == 1:
                    self.manager.logger.info(f"[AUDIO_ROUTER] ✅ Forwarding frame #{self._frame_count} (PARTNER TURN - VAD)")
                await self.push_frame(frame, direction)

            else:
                # Drop frame (not in processing mode)
                if self._frame_count % 50 == 1:
                    state_info = self.manager.state_machine.get_state_info()
                    self.manager.logger.warning(
                        f"[AUDIO_ROUTER] ❌ DROPPING frame #{self._frame_count} - State: {state_info['state']}, "
                        f"PTT: {state_info['ptt_pressed']}, VAD_enable: {state_info['should_enable_vad']}"
                    )
                pass


class TextRouterProcessor(FrameProcessor):
    """
    Routes text frames (transcriptions/translations) to appropriate output.

    - User turn: Send to TTS processor (audio output)
    - Partner turn: Send to frontend (text only)
    """

    def __init__(self, manager: PipelineManager):
        super().__init__()
        self.manager = manager

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        # Handle system frames (StartFrame, EndFrame, etc.) with parent class
        if not isinstance(frame, TextFrame):
            await super().process_frame(frame, direction)
            return

        # Route text frames based on turn state
        current_speaker = self.manager.state_machine.current_speaker

        if self.manager.state_machine.should_output_audio:
            # User turn: forward to TTS
            await self.push_frame(frame, direction)
            # Also emit text for display
            if current_speaker:
                self.manager._emit_text_output(frame.text, current_speaker)

        else:
            # Partner turn: text only, no TTS
            if current_speaker:
                self.manager._emit_text_output(frame.text, current_speaker)
            # Don't forward to TTS


class VADLogger(FrameProcessor):
    """
    Logs VAD (Voice Activity Detection) events for debugging.
    """

    def __init__(self, manager: PipelineManager):
        super().__init__()
        self.manager = manager

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        # Log VAD events (transport generates VAD* frame types)
        if isinstance(frame, (VADUserStartedSpeakingFrame, UserStartedSpeakingFrame)):
            self.manager.logger.info("[VAD] 🎤 Speech STARTED - VAD detected voice activity")
        elif isinstance(frame, (VADUserStoppedSpeakingFrame, UserStoppedSpeakingFrame)):
            self.manager.logger.info("[VAD] 🔇 Speech STOPPED - VAD detected silence")

        # Always forward the frame
        await super().process_frame(frame, direction)


class AudioLevelMonitor(FrameProcessor):
    """
    Monitors audio input levels for visualization.
    """

    def __init__(self, manager: PipelineManager):
        super().__init__()
        self.manager = manager
        self._frame_count = 0

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        # FIRST: Let parent class handle system frames (StartFrame, CancelFrame, etc.)
        await super().process_frame(frame, direction)

        # Monitor AudioRawFrame before forwarding
        if isinstance(frame, AudioRawFrame) and direction == FrameDirection.DOWNSTREAM:
            self._frame_count += 1
            # Log every 100th frame
            if self._frame_count % 100 == 1:
                self.manager.logger.info(f"[AUDIO_MONITOR] Frame #{self._frame_count} received, size={len(frame.audio)} bytes")

            # Calculate audio level
            try:
                import numpy as np
                audio_array = np.frombuffer(frame.audio, dtype=np.int16).astype(np.float32) / 32768.0
                level = calculate_audio_level(audio_array)

                # Determine speaker
                speaker = self.manager.state_machine.current_speaker
                if speaker:
                    self.manager._emit_audio_level(level, speaker)

            except Exception as e:
                self.manager.logger.error(f"Error calculating audio level: {e}")

        # SECOND: Forward ALL frames to next processor in pipeline
        await self.push_frame(frame, direction)
