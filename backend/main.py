"""
Nebula Translate - FastAPI Backend
Real-time voice translation with Pipecat
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings, get_webrtc_config
from models import (
    SessionCreateRequest,
    SessionCreateResponse,
    SessionConfig,
    LanguageCode,
    WebRTCOffer,
    WebRTCAnswer,
    ICECandidate
)
from pipecat.transports.smallwebrtc.request_handler import (
    SmallWebRTCRequestHandler,
    SmallWebRTCRequest,
    SmallWebRTCPatchRequest,
    IceServer,
    ConnectionMode
)
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.transports.base_transport import TransportParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from core import get_session_manager, PipelineManager
from services import (
    STTServiceFactory,
    TTSServiceFactory,
    TranslationServiceFactory,
    VADServiceFactory,
    validate_stt_config,
    validate_tts_config,
    validate_translation_config,
    validate_vad_config,
)
from utils import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Global WebRTC request handler
webrtc_request_handler: SmallWebRTCRequestHandler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global webrtc_request_handler

    # Startup
    logger.info("Starting Nebula Translate backend...")

    # Validate service configurations
    try:
        validate_stt_config()
        validate_tts_config()
        validate_translation_config()
        validate_vad_config()
        logger.info("All service configurations validated")
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise

    # Start session manager
    session_manager = get_session_manager()
    await session_manager.start()
    logger.info("Session manager started")

    # Initialize SmallWebRTC request handler for WebRTC transport
    if settings.transport_mode.value == "webrtc":
        logger.info("Initializing WebRTC request handler...")

        # Prepare ICE servers
        ice_servers_config = []

        # Add STUN server
        ice_servers_config.append(IceServer(urls=[settings.stun_server_url]))

        # Add TURN server if configured
        if settings.turn_server_url:
            ice_servers_config.append(
                IceServer(
                    urls=[settings.turn_server_url],
                    username=settings.turn_username,
                    credential=settings.turn_credential
                )
            )

        # Create request handler
        webrtc_request_handler = SmallWebRTCRequestHandler(
            ice_servers=ice_servers_config,
            connection_mode=ConnectionMode.MULTIPLE  # Support multiple concurrent sessions
        )

        logger.info(f"WebRTC request handler initialized with {len(ice_servers_config)} ICE servers")

    logger.info(f"Backend running on {settings.host}:{settings.port}")
    logger.info(f"Environment: {settings.environment.value}")
    logger.info(f"Transport mode: {settings.transport_mode.value}")

    yield

    # Shutdown
    logger.info("Shutting down Nebula Translate backend...")

    # Close WebRTC request handler if initialized
    if webrtc_request_handler:
        await webrtc_request_handler.close()
        logger.info("WebRTC request handler closed")

    await session_manager.stop()
    logger.info("Backend shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Nebula Translate API",
    description="Real-time AI-powered voice translation",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    session_manager = get_session_manager()
    active_sessions = len(session_manager.list_sessions())

    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.environment.value,
        "transport_mode": settings.transport_mode.value,
        "active_sessions": active_sessions,
        "max_sessions": settings.max_sessions,
    }


# Session management endpoints
@app.post("/api/session/create", response_model=SessionCreateResponse)
async def create_session(request: SessionCreateRequest):
    """
    Create a new translation session.

    Args:
        request: Session configuration (languages)

    Returns:
        Session ID and configuration
    """
    try:
        session_manager = get_session_manager()

        # Create session
        session = session_manager.create_session(
            home_language=request.home_language,
            target_language=request.target_language,
            user_id=request.user_id
        )

        # Prepare response
        config = SessionConfig(
            session_id=session.session_id,
            home_language=session.home_language,
            target_language=session.target_language,
            user_id=session.user_id
        )

        # Include WebRTC config if in WebRTC mode
        webrtc_config = None
        if settings.transport_mode.value == "webrtc":
            webrtc_config = get_webrtc_config()

        logger.info(f"Session created: {session.session_id}")

        return SessionCreateResponse(
            session_id=session.session_id,
            config=config,
            webrtc_config=webrtc_config
        )

    except RuntimeError as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=503, detail=str(e))

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """
    Close and delete a session.

    Args:
        session_id: Session identifier

    Returns:
        Success message
    """
    try:
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        await session_manager.close_session(session_id)

        logger.info(f"Session deleted: {session_id}")

        return {"status": "success", "message": "Session closed"}

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/sessions")
async def list_sessions():
    """List all active sessions."""
    try:
        session_manager = get_session_manager()
        sessions = session_manager.list_sessions()

        return {
            "sessions": [s.dict() for s in sessions],
            "count": len(sessions)
        }

    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Helper function to setup pipeline with WebRTC
async def setup_webrtc_pipeline(session, webrtc_connection):
    """
    Setup Pipecat pipeline with SmallWebRTC transport.

    Args:
        session: Session data
        webrtc_connection: SmallWebRTCConnection instance
    """
    try:
        session_manager = get_session_manager()
        state_machine = session_manager.get_state_machine(session.session_id)

        if not state_machine:
            logger.error(f"State machine not found for session: {session.session_id}")
            return

        # Create pipeline manager for PTT routing logic (before transport)
        pipeline_manager = PipelineManager(
            session=session,
            state_machine=state_machine
        )

        # Create VAD processor FIRST (needed for TransportParams)
        vad_processor = VADServiceFactory.create_vad_processor(
            session_id=session.session_id
        )

        # Create SmallWebRTC transport with VAD analyzer
        transport_params = TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_in_sample_rate=16000,  # Match VAD and STT sample rate
            audio_out_sample_rate=16000,
            video_in_enabled=False,
            video_out_enabled=False,
            audio_in_passthrough=True,  # Pass all audio through for PTT-based routing
            vad_analyzer=vad_processor  # VAD analyzer for speech detection
        )

        transport = SmallWebRTCTransport(
            webrtc_connection=webrtc_connection,
            params=transport_params
        )

        # Register callbacks to send data via WebRTC data channels
        def on_text_output(text: str, speaker: str):
            """Send translated text to frontend via WebRTC data channel."""
            try:
                logger.info(f"[CALLBACK] on_text_output CALLED: text='{text}', speaker={speaker}")

                connection = transport._client._webrtc_connection
                logger.info(f"[CALLBACK] Connection object: {connection}")
                logger.info(f"[CALLBACK] About to call send_app_message()")

                connection.send_app_message({
                    "type": "translation",
                    "text": text,
                    "speaker": speaker
                })

                logger.info(f"[CALLBACK] ✅ send_app_message() returned successfully for: '{text}' (speaker={speaker})")
            except Exception as e:
                logger.error(f"[CALLBACK] ❌ Error sending text output: {e}", exc_info=True)

        def on_audio_level(level: float, speaker: str):
            """Send audio level to frontend via WebRTC data channel."""
            # TEMPORARILY DISABLED to reduce data channel traffic and test translation messages
            pass
            # try:
            #     transport._client._webrtc_connection.send_app_message({
            #         "type": "audio_level",
            #         "level": level,
            #         "speaker": speaker
            #     })
            # except Exception as e:
            #     logger.error(f"[WebRTC] Error sending audio level: {e}")

        def on_thinking(is_thinking: bool):
            """Send thinking indicator to frontend via WebRTC data channel."""
            try:
                transport._client._webrtc_connection.send_app_message({
                    "type": "thinking",
                    "is_thinking": is_thinking
                })
                logger.info(f"[WebRTC] Sent thinking indicator: {is_thinking}")
            except Exception as e:
                logger.error(f"[WebRTC] Error sending thinking indicator: {e}")

        # Register client connection handler
        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            """Called when frontend client connects via WebRTC."""
            logger.info(f"WebRTC client connected (session={session.session_id})")

            # CRITICAL: Transition state machine to CONNECTED to enable audio processing
            state_machine.connect()

            # Log state for debugging
            state_info = state_machine.get_state_info()
            logger.info(f"State after connection: {state_info}")

        # Register client disconnection handler
        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            """Called when frontend client disconnects."""
            logger.info(f"WebRTC client disconnected (session={session.session_id})")

            # Transition state machine to DISCONNECTED
            state_machine.disconnect()

        # Register PTT message handler
        @transport.event_handler("on_app_message")
        async def on_ptt_message(transport, message, sender):
            """Handle PTT messages from frontend."""
            try:
                logger.debug(f"Received app message: {message}")
                if isinstance(message, dict):
                    msg_type = message.get('type')
                    if msg_type == 'ptt_state':
                        ptt_state = message.get('state')
                        if ptt_state == 'pressed':
                            await pipeline_manager.handle_ptt_press()
                            logger.info(f"PTT PRESSED (session={session.session_id})")
                        elif ptt_state == 'released':
                            await pipeline_manager.handle_ptt_release()
                            logger.info(f"PTT RELEASED (session={session.session_id})")
                    else:
                        logger.debug(f"Unknown message type: {msg_type}")
            except Exception as e:
                logger.error(f"Error handling PTT message: {e}")

        # Create service processors
        stt_processor = STTServiceFactory.create_stt_processor(
            session.home_language,
            session.session_id
        )

        tts_processor = TTSServiceFactory.create_tts_processor(
            session.target_language,
            session_id=session.session_id
        )

        translation_processor = TranslationServiceFactory.create_translation_processor(
            source_language=session.home_language,
            target_language=session.target_language,
            session_id=session.session_id
        )

        # Set services in pipeline manager
        pipeline_manager.set_services(
            stt_processor=stt_processor,
            tts_processor=tts_processor,
            translation_processor=translation_processor,
            vad_processor=vad_processor
        )

        # Set WebRTC callbacks on pipeline manager
        pipeline_manager.on_text_output = on_text_output
        pipeline_manager.on_audio_level = on_audio_level
        pipeline_manager.on_thinking = on_thinking
        logger.info("[WebRTC] Pipeline callbacks registered for data channel communication")

        # Build pipeline with transport and PTT routing processors
        from core.pipeline_manager import AudioRouterProcessor, TextRouterProcessor, AudioLevelMonitor, VADLogger

        audio_router = AudioRouterProcessor(pipeline_manager)
        text_router = TextRouterProcessor(pipeline_manager)
        audio_level_monitor = AudioLevelMonitor(pipeline_manager)
        vad_logger = VADLogger(pipeline_manager)

        pipeline = Pipeline([
            transport.input(),           # WebRTC audio input (VAD handled by transport)
            audio_level_monitor,         # Monitor audio levels
            vad_logger,                  # Log VAD events for debugging
            audio_router,                # Route based on PTT state
            stt_processor,               # Speech-to-text
            translation_processor,       # Translation
            text_router,                 # Route text based on state
            tts_processor,               # Text-to-speech (only for user turn)
            transport.output(),          # WebRTC audio output
        ])

        # Log pipeline structure for debugging
        logger.info("[PIPELINE] Pipeline created with the following processors:")
        for i, proc in enumerate(pipeline.processors):
            proc_name = proc.__class__.__name__
            prev_name = proc.previous.__class__.__name__ if proc.previous else "None"
            next_name = proc.next.__class__.__name__ if proc.next else "None"
            logger.info(f"  [{i}] {proc_name} (prev={prev_name}, next={next_name})")

        # Create and run pipeline task
        task = PipelineTask(pipeline)
        runner = PipelineRunner()

        # Start the pipeline as a background task (non-blocking)
        # This allows the WebRTC callback to complete and return the answer
        pipeline_task = asyncio.create_task(runner.run(task))

        # Wait to allow StartFrame to propagate through the pipeline
        # This prevents the race condition where audio arrives before processors are initialized
        # The runner.run() task immediately sends StartFrame down the pipeline,
        # With 11 processors and logging overhead, we need ~1.5s to ensure all processors receive StartFrame
        logger.info("[PIPELINE] Waiting 1.5s for StartFrame to propagate through all 11 processors...")
        await asyncio.sleep(1.5)
        logger.info("[PIPELINE] StartFrame propagation wait complete, pipeline should be ready")
        logger.info(f"Pipeline initialization wait completed for session: {session.session_id}")

        # Store runner, task, and pipeline manager in session for cleanup
        session_manager._pipelines[session.session_id] = {
            'pipeline': pipeline,
            'task': task,
            'runner': runner,
            'transport': transport,
            'background_task': pipeline_task,
            'pipeline_manager': pipeline_manager
        }

        logger.info(f"WebRTC pipeline setup completed for session: {session.session_id}")

    except Exception as e:
        logger.error(f"Error setting up WebRTC pipeline: {e}")
        raise


# WebRTC endpoints for SmallWebRTC transport
@app.post("/api/webrtc/offer")
async def handle_webrtc_offer(request: dict):
    """
    Handle WebRTC offer from client using Pipecat SmallWebRTC.

    Args:
        request: SmallWebRTC request dict containing sdp, type, pc_id, request_data

    Returns:
        WebRTC answer with sdp, type, and pc_id
    """
    try:
        if not webrtc_request_handler:
            raise HTTPException(
                status_code=503,
                detail="WebRTC not enabled. Set TRANSPORT_MODE=webrtc in .env"
            )

        # Parse SmallWebRTC request
        webrtc_request = SmallWebRTCRequest.from_dict(request)

        # Extract session_id from request_data
        request_data = webrtc_request.request_data or {}
        session_id = request_data.get("session_id")

        if not session_id:
            raise HTTPException(status_code=400, detail="session_id required in request_data")

        # Get session
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Define connection callback
        async def on_webrtc_connection(webrtc_connection):
            """Called when WebRTC connection is established."""
            logger.info(f"WebRTC connection established for session: {session_id}")

            # Setup pipeline with this WebRTC connection
            await setup_webrtc_pipeline(session, webrtc_connection)

        # Handle the WebRTC request and get answer
        answer = await webrtc_request_handler.handle_web_request(
            webrtc_request,
            on_webrtc_connection
        )

        logger.info(f"WebRTC offer processed for session: {session_id}, pc_id: {answer.get('pc_id')}")

        return answer  # Returns {sdp, type, pc_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling WebRTC offer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/webrtc/offer")
async def handle_webrtc_patch(request: dict):
    """
    Handle WebRTC PATCH request for ICE candidates.

    Args:
        request: Patch request dict containing pc_id and candidates

    Returns:
        Success status
    """
    try:
        if not webrtc_request_handler:
            raise HTTPException(
                status_code=503,
                detail="WebRTC not enabled. Set TRANSPORT_MODE=webrtc in .env"
            )

        # Parse PATCH request - manually construct IceCandidate objects
        from pipecat.transports.smallwebrtc.request_handler import IceCandidate

        pc_id = request.get("pc_id") or request.get("pcId")
        candidates_data = request.get("candidates", [])

        # Convert candidate dicts to IceCandidate objects
        candidates = []
        for cand_dict in candidates_data:
            # Handle both snake_case and camelCase field names
            candidate = IceCandidate(
                candidate=cand_dict.get("candidate"),
                sdp_mid=cand_dict.get("sdp_mid") or cand_dict.get("sdpMid"),
                sdp_mline_index=cand_dict.get("sdp_mline_index") or cand_dict.get("sdpMLineIndex")
            )
            candidates.append(candidate)

        patch_request = SmallWebRTCPatchRequest(
            pc_id=pc_id,
            candidates=candidates
        )

        # Handle ICE candidates
        await webrtc_request_handler.handle_patch_request(patch_request)

        logger.debug(f"ICE candidates added for pc_id: {patch_request.pc_id}")

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling WebRTC PATCH: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/webrtc/ice-candidate")
async def handle_ice_candidate(candidate: ICECandidate):
    """
    Handle ICE candidate from client (legacy endpoint - kept for compatibility).

    Args:
        candidate: ICE candidate data

    Returns:
        Success status
    """
    try:
        # Note: SmallWebRTC transport uses PATCH endpoint instead
        # This endpoint is kept for compatibility with custom implementations
        logger.info(f"ICE candidate received for session: {candidate.session_id}")

        return {"status": "success", "message": "ICE candidate added (legacy endpoint)"}

    except Exception as e:
        logger.error(f"Error handling ICE candidate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Configuration endpoints
@app.get("/api/config/languages")
async def get_supported_languages():
    """Get list of supported languages."""
    from models import LANGUAGE_NAMES

    return {
        "languages": [
            {
                "code": code.value,
                "name": name
            }
            for code, name in LANGUAGE_NAMES.items()
        ]
    }


@app.get("/api/config/models")
async def get_supported_models():
    """Get list of supported translation models."""
    from services import list_supported_models

    models = list_supported_models()

    return {
        "models": [
            {
                "id": model_id,
                "description": desc
            }
            for model_id, desc in models.items()
        ],
        "default": settings.openrouter_model
    }


@app.get("/api/config/voices")
async def get_available_voices():
    """Get list of available TTS voices."""
    from services import list_available_voices

    voices = list_available_voices()

    return {
        "voices": [
            {
                "id": voice_id,
                "description": desc
            }
            for voice_id, desc in voices.items()
        ],
        "default": settings.openai_tts_voice
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "detail": str(exc)}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
