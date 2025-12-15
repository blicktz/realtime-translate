# Nebula Translate 🌐

**Real-time AI-powered voice translation for face-to-face conversations**

A mobile-first Progressive Web App (PWA) that provides high-fidelity, real-time voice translation using a strict Push-to-Talk (PTT) interface. Built with Pipecat, OpenAI, and Next.js.

## ✨ Features

- **Push-to-Talk Interface**: Clear separation of user/partner turns
- **Real-time Translation**: Powered by OpenAI Whisper (STT), GPT-4/Claude (Translation), and OpenAI TTS
- **Mobile-Optimized**: PWA with offline capabilities, touch gestures, and haptic feedback
- **Cyberpunk UI**: Futuristic, high-contrast design optimized for outdoor visibility
- **Bilingual Support**: 25+ languages with automatic voice selection
- **Low Latency**: <2s end-to-end translation on 4G/WiFi

## 🏗️ Architecture

### Tech Stack

**Backend (Python)**
- Pipecat: Voice agent orchestration
- FastAPI: REST/WebSocket API
- OpenAI Whisper: Speech-to-text
- OpenAI TTS: Text-to-speech
- OpenRouter: LLM translation (GPT-4, Claude)
- Silero VAD: Voice activity detection

**Frontend (TypeScript)**
- Next.js 14: App Router, PWA support
- React 18: UI components
- Zustand: State management
- Tailwind CSS: Cyberpunk styling
- Web Audio API: Audio visualization

### Project Structure

```
real-translate/
├── backend/                # Python backend with Pipecat
│   ├── main.py            # FastAPI entry point
│   ├── config.py          # Configuration
│   ├── core/              # Pipeline, session, state machine
│   ├── services/          # STT, TTS, translation, VAD
│   ├── transports/        # WebSocket/WebRTC
│   ├── models/            # Data models
│   ├── utils/             # Logging, audio utilities
│   ├── pipecat/           # Pipecat submodule
│   └── Dockerfile         # Container configuration
├── frontend/              # Next.js PWA frontend
│   ├── app/               # Next.js App Router
│   ├── components/        # React components
│   ├── store/             # Zustand stores
│   ├── hooks/             # Custom hooks
│   ├── lib/               # Utilities, types
│   └── public/            # Static assets, PWA icons
└── docs/                  # Documentation
    ├── prd.md             # Product requirements
    └── implementation-plan.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key
- OpenRouter API key

### 1. Clone with Pipecat Submodule

```bash
git clone https://github.com/your-org/real-translate.git
cd real-translate
git submodule update --init --recursive
```

### 2. Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run development server
python main.py
```

Backend will start on `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
# Create .env.local with:
# NEXT_PUBLIC_API_URL=http://localhost:8000
# NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Run development server
npm run dev
```

Frontend will start on `http://localhost:3000`

### 4. Open in Browser

Visit `http://localhost:3000` on your mobile device or desktop browser.

## 📱 Usage

### Basic Flow

1. **Connect**: Tap the "CONNECT" button to establish a session
2. **Configure Languages**: Open settings (⚙️) to select home and target languages
3. **User Turn (PTT Pressed)**:
   - Hold the PTT button
   - Speak into microphone
   - Release button
   - Partner hears translation audio
   - You see your original text (right side)

4. **Partner Turn (PTT Released)**:
   - Partner speaks
   - You see translated text (left side)
   - No audio output (text only)

### PTT State Logic

| PTT State | Input Source | Output Mode | Display |
|-----------|--------------|-------------|---------|
| **Pressed** | User microphone | Audio (TTS) | Home language text (right) |
| **Released** | Partner microphone (VAD) | Text only | Translated home language (left) |

## 🔧 Configuration

### Backend Environment Variables

Required in `backend/.env`:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_STT_MODEL=whisper-1
OPENAI_TTS_MODEL=tts-1

# OpenRouter Configuration
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# Server Configuration
HOST=0.0.0.0
PORT=8000
ALLOWED_ORIGINS=http://localhost:3000

# VAD Configuration
VAD_CONFIDENCE_THRESHOLD=0.7
VAD_START_SECS=0.2
VAD_STOP_SECS=0.8
```

### Frontend Environment Variables

Required in `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## 🎨 Features Overview

### Mobile Optimizations

- **PWA Support**: Install to home screen, works offline
- **Touch Gestures**: Long press PTT, swipe to settings
- **Haptic Feedback**: Vibration on button press/release
- **Screen Wake Lock**: Prevents screen sleep during sessions
- **Safe Area Handling**: iPhone notch/home indicator support
- **Adaptive Quality**: Network-aware audio bitrate

### Audio Processing

- **Voice Activity Detection (VAD)**: Silero VAD for partner speech detection
- **Real-time Visualization**: 50-bar audio visualizer with color coding
- **Echo Cancellation**: Built-in noise suppression
- **Auto-gain Control**: Consistent volume levels

### Translation Quality

- **Context-Aware**: LLM translation preserves tone and nuance
- **Multiple Models**: GPT-4, Claude 3.5 Sonnet with fallbacks
- **Low Latency**: Streaming transcription and translation

## 📦 Deployment

### Backend (Docker)

```bash
cd backend
docker build -t nebula-translate-backend .
docker run -p 8000:8000 --env-file .env nebula-translate-backend
```

### Frontend (Vercel)

```bash
cd frontend
npm run build
# Deploy to Vercel/Netlify
```

Or use Docker:

```bash
cd frontend
docker build -t nebula-translate-frontend .
docker run -p 3000:3000 nebula-translate-frontend
```

### Production Requirements

- Backend: AWS ECS, Google Cloud Run, or similar
- Frontend: Vercel, Netlify, or CDN
- WebRTC: TURN server for NAT traversal (Twilio, Cloudflare)
- SSL/TLS: Required for PWA and WebRTC

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest
```

### Frontend Tests

```bash
cd frontend
npm run test
```

### Manual Testing

1. Test PTT press/release on mobile
2. Verify audio output during user turn
3. Verify text-only output during partner turn
4. Test language switching
5. Test reconnection after network drop

## 🐛 Troubleshooting

### "WebSocket connection failed"
- Check backend is running on correct port
- Verify CORS settings in backend config
- Check firewall rules

### "Microphone permission denied"
- Enable microphone permissions in browser settings
- HTTPS required for microphone access (use ngrok for local testing)

### "No audio output"
- Check iOS silent mode (switch on side)
- Verify AudioContext is unlocked (tap screen first)
- Check speaker/headphone connection

### High latency
- Check network connection (use WiFi)
- Monitor backend logs for service latencies
- Consider using faster translation model

## 📝 Development

### Adding New Languages

1. Update `backend/models/enums.py`:
   ```python
   class LanguageCode(str, Enum):
       NEW_LANG = "xx"
   ```

2. Update `LANGUAGE_NAMES` dict with display name

3. Restart backend

### Customizing UI Theme

Edit `frontend/tailwind.config.ts`:

```typescript
colors: {
  'cyber-cyan': '#00ffff',    // Primary accent
  'cyber-magenta': '#ff00ff',  // Secondary accent
  'cyber-dark': '#0a0a0f',     // Background
}
```

## 📚 Documentation

- [Product Requirements Document (PRD)](./docs/prd.md)
- [Implementation Plan](./docs/implementation-plan.md)
- [Backend API Documentation](./backend/README.md)
- [Pipecat Documentation](https://docs.pipecat.ai)

## 🔒 Security

- API keys stored in environment variables only
- Rate limiting on backend API
- Input sanitization for user text
- CORS allowlist for production
- No audio data stored or logged

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly on mobile devices
5. Submit a pull request

## 📄 License

Proprietary - Nebula Translate

## 🙏 Acknowledgments

- [Pipecat](https://github.com/pipecat-ai/pipecat) - Voice agent framework
- OpenAI - Whisper STT and TTS
- Anthropic - Claude translation models
- Silero - Voice activity detection

---

Built with ❤️ for seamless cross-language communication
