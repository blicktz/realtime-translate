# Nebula Translate - Backend

Real-time AI-powered voice translation backend built with **Pipecat**, **FastAPI**, and AI services.

## Architecture

- **Framework**: FastAPI for REST/WebSocket API
- **Audio Pipeline**: Pipecat for frame-based audio processing
- **STT**: OpenAI Whisper API
- **TTS**: OpenAI TTS API
- **Translation**: OpenRouter (GPT-4, Claude, etc.)
- **VAD**: Silero Voice Activity Detection
- **Dependency Management**: Poetry

## Project Structure

```
backend/
├── main.py                  # FastAPI application entry point
├── config.py                # Configuration management
├── pyproject.toml          # Poetry dependencies & config
├── poetry.lock             # Locked dependencies
├── Dockerfile              # Container configuration
├── pipecat/                # Pipecat submodule
├── core/                   # Core business logic
│   ├── pipeline_manager.py # Pipecat pipeline orchestration
│   ├── session_manager.py  # Session lifecycle management
│   └── state_machine.py    # PTT state machine
├── services/               # AI service integrations
│   ├── stt_service.py      # Speech-to-text (Whisper)
│   ├── tts_service.py      # Text-to-speech (OpenAI TTS)
│   ├── translation_service.py  # LLM translation (OpenRouter)
│   └── vad_service.py      # Voice activity detection (Silero)
├── transports/             # Transport layers
│   ├── websocket_transport.py  # WebSocket (development)
│   └── webrtc_transport.py     # WebRTC (production)
├── models/                 # Data models
│   ├── enums.py
│   ├── messages.py
│   └── session.py
└── utils/                  # Utilities
    ├── logger.py
    └── audio_utils.py
```

## Setup

### Prerequisites

- Python 3.10+
- Poetry 1.7+
- Git (for Pipecat submodule)

### 1. Install Poetry

If you don't have Poetry installed:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Or on macOS with Homebrew:

```bash
brew install poetry
```

### 2. Clone with Pipecat Submodule

```bash
git submodule update --init --recursive
```

### 3. Install Dependencies

```bash
cd backend
poetry install
```

This will:
- Create a virtual environment in `.venv/`
- Install all dependencies from `pyproject.toml`
- Lock versions in `poetry.lock`

### 4. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required environment variables:
- `OPENAI_API_KEY`: OpenAI API key for Whisper STT and TTS
- `OPENROUTER_API_KEY`: OpenRouter API key for LLM translation

### 5. Install Pipecat from Submodule

```bash
poetry run pip install -e ./pipecat
```

### 6. Run Development Server

Using Poetry scripts:

```bash
poetry run dev
```

Or directly with uvicorn:

```bash
poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or activate the virtual environment first:

```bash
poetry shell
python main.py
```

## Poetry Commands

### Dependency Management

```bash
# Add a new dependency
poetry add package-name

# Add a development dependency
poetry add --group dev package-name

# Update all dependencies
poetry update

# Update a specific package
poetry update package-name

# Show installed packages
poetry show

# Show dependency tree
poetry show --tree
```

### Running Scripts

```bash
# Run development server with auto-reload
poetry run dev

# Run production server
poetry run start

# Run tests
poetry run pytest

# Format code with Black
poetry run black .

# Lint with Ruff
poetry run ruff check .

# Type check with MyPy
poetry run mypy .
```

### Virtual Environment

```bash
# Activate virtual environment
poetry shell

# Show virtual environment info
poetry env info

# Remove virtual environment
poetry env remove python
```

## Docker

### Build Image

```bash
docker build -t nebula-translate-backend .
```

### Run Container

```bash
docker run -p 8000:8000 --env-file .env nebula-translate-backend
```

### Docker Compose

```yaml
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    volumes:
      - ./logs:/app/logs
```

## API Endpoints

### Health Check
```
GET /health
```

### Session Management

**Create Session**
```
POST /api/session/create
Body: {
  "home_language": "en",
  "target_language": "es"
}
```

**Delete Session**
```
DELETE /api/session/{session_id}
```

**List Sessions**
```
GET /api/sessions
```

### WebSocket Connection

```
WS /ws/session/{session_id}
```

Message types:
- `ptt_state`: PTT button press/release
- `audio_data`: Input audio from microphone
- `translation`: Translated text output
- `audio_output`: TTS audio output

### Configuration

**Supported Languages**
```
GET /api/config/languages
```

**Translation Models**
```
GET /api/config/models
```

**TTS Voices**
```
GET /api/config/voices
```

## Core Concepts

### PTT State Machine

The application uses a strict Push-to-Talk (PTT) state machine:

- **PTT Pressed** (User Turn):
  - User speaks → STT → Translation → TTS → Audio output
  - Display: Home language text (right side)

- **PTT Released** (Partner Turn):
  - VAD listens → Partner speaks → STT → Translation → Text only
  - Display: Translated home language text (left side)

### Pipecat Pipeline

The audio processing pipeline uses Pipecat's frame-based architecture:

```
AudioInput → VAD → STT → Translation → TTS → AudioOutput
```

Pipeline routing is dynamic based on PTT state:
- User turn: Full pipeline with TTS
- Partner turn: Pipeline without TTS (text only)

## Development

### Code Quality

```bash
# Format code
poetry run black .

# Lint
poetry run ruff check .

# Type check
poetry run mypy .

# Run all checks
poetry run black . && poetry run ruff check . && poetry run mypy .
```

### Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=. --cov-report=html

# Run specific test file
poetry run pytest tests/test_session.py

# Run with verbose output
poetry run pytest -v
```

### Adding New Dependencies

```bash
# Production dependency
poetry add package-name

# Development dependency
poetry add --group dev package-name

# With version constraint
poetry add "package-name>=1.0,<2.0"

# From git repository
poetry add git+https://github.com/user/repo.git
```

### Testing WebSocket Connection

Use `wscat` for testing:

```bash
npm install -g wscat

# Create session first (get session_id)
curl -X POST http://localhost:8000/api/session/create \
  -H "Content-Type: application/json" \
  -d '{"home_language":"en","target_language":"es"}'

# Connect to WebSocket
wscat -c ws://localhost:8000/ws/session/{session_id}

# Send PTT press
{"type":"ptt_state","state":"pressed"}

# Send audio data (base64 encoded)
{"type":"audio_data","audio":"<base64_pcm16_audio>"}

# Send PTT release
{"type":"ptt_state","state":"released"}
```

## Service Configuration

### OpenAI (STT/TTS)

```python
OPENAI_API_KEY=your_key
OPENAI_STT_MODEL=whisper-1
OPENAI_TTS_MODEL=tts-1
OPENAI_TTS_VOICE=alloy
```

### OpenRouter (Translation)

```python
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

### VAD (Voice Activity Detection)

```python
VAD_CONFIDENCE_THRESHOLD=0.7
VAD_START_SECS=0.2
VAD_STOP_SECS=0.8
```

## Production Deployment

### Environment Variables

Production requires:
- `ENVIRONMENT=production`
- `ALLOWED_ORIGINS`: Frontend domain(s)
- `TURN_SERVER_URL`: TURN server for WebRTC (if using WebRTC mode)
- All API keys

### Build for Production

```bash
# Install only production dependencies
poetry install --without dev

# Export requirements.txt (if needed for legacy systems)
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

### Docker Production Build

```bash
docker build -t nebula-translate-backend:latest .
docker tag nebula-translate-backend:latest registry.example.com/nebula-backend:latest
docker push registry.example.com/nebula-backend:latest
```

## Monitoring

Key metrics to monitor:
- Active sessions count
- Average latency (STT, Translation, TTS)
- Error rates per service
- WebSocket connection stability

Access metrics via `/api/sessions` endpoint.

## Troubleshooting

### "Poetry not found"
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### "Module not found" errors
```bash
# Make sure you're in the virtual environment
poetry shell

# Or reinstall dependencies
poetry install
```

### "OpenAI API key not configured"
- Ensure `.env` file exists with `OPENAI_API_KEY`

### "Failed to create STT service"
- Verify API key is valid
- Check network connectivity to OpenAI

### "Pipecat import errors"
```bash
# Install Pipecat from submodule
poetry run pip install -e ./pipecat
```

### High latency
- Monitor service-specific latencies via session metrics
- Consider using faster translation models
- Check network conditions

## Logging

Logs are configured via `utils/logger.py`:
- Development: Human-readable console output
- Production: Structured JSON logs to `logs/` directory

Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## License

Proprietary - Nebula Translate

## Contributing

1. Install Poetry
2. Clone repository with submodules
3. Run `poetry install`
4. Create feature branch
5. Make changes
6. Run tests: `poetry run pytest`
7. Format code: `poetry run black .`
8. Submit PR
