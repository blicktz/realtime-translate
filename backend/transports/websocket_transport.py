"""
WebSocket transport layer for development.
Simpler alternative to WebRTC for local testing.
"""

import json
import asyncio
from typing import Optional, Dict
from fastapi import WebSocket, WebSocketDisconnect
from models import (
    PTTMessage,
    PTTState,
    ConnectionStateMessage,
    ErrorMessage,
    MessageType
)
from core import SessionManager, PipelineManager
from utils import SessionLogger

logger = SessionLogger("websocket")


class WebSocketHandler:
    """
    Handles WebSocket connections for development transport.

    Provides bidirectional communication:
    - Receives: PTT state, audio data, control messages
    - Sends: Translations, audio output, state updates
    """

    def __init__(
        self,
        websocket: WebSocket,
        session_id: str,
        session_manager: SessionManager,
        pipeline_manager: PipelineManager
    ):
        self.websocket = websocket
        self.session_id = session_id
        self.session_manager = session_manager
        self.pipeline_manager = pipeline_manager
        self.logger = SessionLogger(session_id)

        # Connection state
        self.is_connected = False

    async def handle_connection(self):
        """Main handler for WebSocket connection lifecycle."""
        try:
            # Accept WebSocket connection
            await self.websocket.accept()
            self.is_connected = True

            self.logger.info("WebSocket connected")

            # Send connection success message
            await self._send_connection_state("connected")

            # Register pipeline callbacks
            self._register_pipeline_callbacks()

            # Start message handling loop
            await self._message_loop()

        except WebSocketDisconnect:
            self.logger.info("WebSocket disconnected by client")

        except Exception as e:
            self.logger.error(f"WebSocket error: {e}")
            await self._send_error("internal_error", str(e))

        finally:
            self.is_connected = False
            await self.cleanup()

    async def _message_loop(self):
        """Main message receiving loop."""
        while self.is_connected:
            try:
                # Receive message from client
                message_raw = await self.websocket.receive_text()
                message_data = json.loads(message_raw)

                # Handle different message types
                await self._handle_message(message_data)

            except WebSocketDisconnect:
                break

            except json.JSONDecodeError as e:
                self.logger.warning(f"Invalid JSON received: {e}")

            except Exception as e:
                self.logger.error(f"Error processing message: {e}")

    async def _handle_message(self, data: dict):
        """Handle incoming messages from client."""
        message_type = data.get("type")

        if message_type == MessageType.PTT_STATE.value:
            # PTT state change
            await self._handle_ptt_state(data)

        elif message_type == "audio_data":
            # Audio input from microphone
            await self._handle_audio_input(data)

        else:
            self.logger.warning(f"Unknown message type: {message_type}")

    async def _handle_ptt_state(self, data: dict):
        """Handle PTT button press/release."""
        state = data.get("state")

        if state == PTTState.PRESSED.value:
            await self.pipeline_manager.handle_ptt_press()
            self.logger.debug("PTT pressed")

        elif state == PTTState.RELEASED.value:
            await self.pipeline_manager.handle_ptt_release()
            self.logger.debug("PTT released")

    async def _handle_audio_input(self, data: dict):
        """Handle incoming audio data."""
        # Audio data should be base64 encoded in the message
        import base64

        audio_base64 = data.get("audio")
        if not audio_base64:
            return

        try:
            # Decode audio data
            audio_bytes = base64.b64decode(audio_base64)

            # Process through pipeline
            await self.pipeline_manager.process_audio_input(audio_bytes)

        except Exception as e:
            self.logger.error(f"Error processing audio input: {e}")

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
        import base64

        # Encode audio as base64 for WebSocket transmission
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        await self._send_message({
            "type": "audio_output",
            "audio": audio_base64
        })

    async def _on_text_output(self, text: str, speaker: str):
        """Callback when translation text is ready."""
        await self._send_message({
            "type": MessageType.TRANSLATION.value,
            "text": text,
            "speaker": speaker
        })

    async def _on_audio_level(self, level: float, speaker: str):
        """Callback for audio level updates."""
        await self._send_message({
            "type": MessageType.AUDIO_LEVEL.value,
            "level": level,
            "speaker": speaker
        })

    async def _on_thinking(self, is_thinking: bool):
        """Callback for thinking indicator."""
        await self._send_message({
            "type": MessageType.THINKING.value,
            "is_thinking": is_thinking
        })

    async def _send_connection_state(self, state: str):
        """Send connection state update."""
        await self._send_message({
            "type": MessageType.CONNECTION_STATE.value,
            "state": state
        })

    async def _send_error(self, code: str, message: str):
        """Send error message."""
        await self._send_message({
            "type": MessageType.ERROR.value,
            "error_code": code,
            "error_message": message
        })

    async def _send_message(self, data: dict):
        """Send message to client."""
        if not self.is_connected:
            return

        try:
            await self.websocket.send_text(json.dumps(data))
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")

    async def cleanup(self):
        """Cleanup resources."""
        self.is_connected = False

        # Stop pipeline
        if self.pipeline_manager:
            await self.pipeline_manager.stop()

        self.logger.info("WebSocket handler cleaned up")
