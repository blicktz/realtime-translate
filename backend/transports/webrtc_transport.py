"""
WebRTC transport layer for production using Pipecat SmallWebRTC.
Provides low-latency peer-to-peer audio/video transport.
"""

import asyncio
from typing import Optional, Dict
from fastapi import WebSocket
from models import PTTMessage, PTTState
from core import SessionManager, PipelineManager
from utils import SessionLogger

# Import Pipecat WebRTC transport
try:
    from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
    from pipecat.frames.frames import AudioRawFrame
except ImportError:
    raise ImportError("Pipecat WebRTC transport not available. Install pipecat with WebRTC support.")

logger = SessionLogger("webrtc")


class WebRTCHandler:
    """
    Handles WebRTC connections using Pipecat's SmallWebRTC transport.

    This handler manages the WebRTC peer connection for real-time
    audio streaming between the client and Pipecat pipeline.
    """

    def __init__(
        self,
        session_id: str,
        session_manager: SessionManager,
        pipeline_manager: PipelineManager
    ):
        self.session_id = session_id
        self.session_manager = session_manager
        self.pipeline_manager = pipeline_manager
        self.logger = SessionLogger(session_id)

        self.transport: Optional[SmallWebRTCTransport] = None
        self.is_connected = False

    async def initialize_transport(self):
        """Initialize the SmallWebRTC transport for this session."""
        try:
            # Create SmallWebRTC transport
            # This will handle the WebRTC peer connection
            self.transport = SmallWebRTCTransport()

            self.logger.info("WebRTC transport initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize WebRTC transport: {e}")
            raise

    async def handle_offer(self, offer: dict) -> dict:
        """
        Handle WebRTC offer from client.

        Args:
            offer: SDP offer from client

        Returns:
            SDP answer for client
        """
        try:
            if not self.transport:
                await self.initialize_transport()

            # Process offer and generate answer
            # This will be handled by the Pipecat SmallWebRTC transport
            answer = await self.transport.process_offer(offer)

            self.logger.info("WebRTC offer processed, answer generated")
            return answer

        except Exception as e:
            self.logger.error(f"Error processing WebRTC offer: {e}")
            raise

    async def handle_ice_candidate(self, candidate: dict):
        """
        Handle ICE candidate from client.

        Args:
            candidate: ICE candidate data
        """
        try:
            if self.transport:
                await self.transport.add_ice_candidate(candidate)
                self.logger.debug(f"ICE candidate added: {candidate.get('candidate', '')[:50]}...")

        except Exception as e:
            self.logger.error(f"Error adding ICE candidate: {e}")

    async def start_streaming(self):
        """Start the WebRTC streaming session."""
        try:
            if not self.transport:
                raise RuntimeError("Transport not initialized")

            self.is_connected = True

            # Register pipeline callbacks for audio output
            self._register_pipeline_callbacks()

            # Start transport
            await self.transport.start()

            self.logger.info("WebRTC streaming started")

        except Exception as e:
            self.logger.error(f"Error starting WebRTC streaming: {e}")
            raise

    def _register_pipeline_callbacks(self):
        """Register callbacks for pipeline events."""
        # Audio output callback
        self.pipeline_manager.on_audio_output = self._on_audio_output

        # Text output callback
        self.pipeline_manager.on_text_output = self._on_text_output

        # Audio level callback
        self.pipeline_manager.on_audio_level = self._on_audio_level

        # Thinking indicator callback
        self.pipeline_manager.on_thinking = self._on_thinking

    async def _on_audio_output(self, audio_data: bytes):
        """Callback when TTS audio is ready."""
        if not self.transport or not self.is_connected:
            return

        try:
            # Send audio via WebRTC transport
            # The transport will handle encoding and streaming
            await self.transport.send_audio(audio_data)

        except Exception as e:
            self.logger.error(f"Error sending audio output: {e}")

    async def _on_text_output(self, text: str, speaker: str):
        """Callback when translation text is ready."""
        if not self.transport or not self.is_connected:
            return

        try:
            # Send text message via data channel
            await self.transport.send_message({
                "type": "translation",
                "text": text,
                "speaker": speaker
            })

        except Exception as e:
            self.logger.error(f"Error sending text output: {e}")

    async def _on_audio_level(self, level: float, speaker: str):
        """Callback for audio level updates."""
        if not self.transport or not self.is_connected:
            return

        try:
            await self.transport.send_message({
                "type": "audio_level",
                "level": level,
                "speaker": speaker
            })

        except Exception as e:
            self.logger.error(f"Error sending audio level: {e}")

    async def _on_thinking(self, is_thinking: bool):
        """Callback for thinking indicator."""
        if not self.transport or not self.is_connected:
            return

        try:
            await self.transport.send_message({
                "type": "thinking",
                "is_thinking": is_thinking
            })

        except Exception as e:
            self.logger.error(f"Error sending thinking indicator: {e}")

    async def handle_ptt_message(self, message: dict):
        """Handle PTT state change message."""
        state = message.get("state")

        if state == "pressed":
            await self.pipeline_manager.handle_ptt_press()
            self.logger.debug("PTT pressed")

        elif state == "released":
            await self.pipeline_manager.handle_ptt_release()
            self.logger.debug("PTT released")

    async def process_audio_input(self, audio_data: bytes):
        """
        Process incoming audio data from client.

        Args:
            audio_data: Raw PCM16 audio bytes
        """
        if not self.is_connected:
            return

        try:
            # Process through pipeline
            await self.pipeline_manager.process_audio_input(audio_data)

        except Exception as e:
            self.logger.error(f"Error processing audio input: {e}")

    async def cleanup(self):
        """Cleanup resources."""
        self.is_connected = False

        # Stop pipeline
        if self.pipeline_manager:
            await self.pipeline_manager.stop()

        # Close transport
        if self.transport:
            await self.transport.close()
            self.transport = None

        self.logger.info("WebRTC handler cleaned up")
