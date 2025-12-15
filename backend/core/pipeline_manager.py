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
    CancelFrame
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
            self.translation_processor
        ]):
            raise RuntimeError("Services must be set before initializing pipeline")

        # Create custom processors for routing and callbacks
        audio_router = AudioRouterProcessor(self)
        text_router = TextRouterProcessor(self)
        audio_level_monitor = AudioLevelMonitor(self)

        # Build the pipeline
        # The pipeline flow depends on the current state machine state
        # Note: VAD is not included in pipeline as speech routing is controlled by PTT state
        self.pipeline = Pipeline([
            audio_level_monitor,    # Monitor input audio levels
            audio_router,           # Route based on PTT state
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
        if not isinstance(frame, AudioRawFrame):
            await super().process_frame(frame, direction)
            return

        # Only process downstream audio frames
        if direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return

        # Log audio frame receipt (throttled to every 100 frames)
        self._frame_count += 1
        if self._frame_count % 100 == 1:
            state_info = self.manager.state_machine.get_state_info()
            self.manager.logger.debug(
                f"Audio frame received (count={self._frame_count}), "
                f"state={state_info['state']}, "
                f"is_user_turn={state_info['ptt_pressed']}, "
                f"should_enable_vad={state_info['should_enable_vad']}"
            )

        # Route audio frames based on PTT state
        if self.manager.state_machine.is_user_turn:
            # User turn: always process
            await self.push_frame(frame, direction)

        elif self.manager.state_machine.should_enable_vad:
            # Partner turn: only process if VAD enabled
            await self.push_frame(frame, direction)

        else:
            # Drop frame (not in processing mode)
            if self._frame_count == 1:
                self.manager.logger.warning(
                    f"Dropping audio frames - state: {self.manager.state_machine.state.value}, "
                    f"PTT: {self.manager.state_machine.is_user_turn}, "
                    f"VAD should enable: {self.manager.state_machine.should_enable_vad}"
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


class AudioLevelMonitor(FrameProcessor):
    """
    Monitors audio input levels for visualization.
    """

    def __init__(self, manager: PipelineManager):
        super().__init__()
        self.manager = manager

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        # CRITICAL: Call parent first to handle StartFrame and other system frames
        await super().process_frame(frame, direction)

        if isinstance(frame, AudioRawFrame) and direction == FrameDirection.DOWNSTREAM:
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
