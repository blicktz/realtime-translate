# Nebula Translate - Setup Guide

Complete setup instructions for the Pipecat-powered real-time translation app.

## ✅ Changes Made

### Frontend Updates
- ✅ Updated `@pipecat-ai/client-js` to `^1.5.0` (from non-existent `^0.1.0`)
- ✅ Added `@pipecat-ai/small-webrtc-transport` for WebRTC connectivity
- ✅ Created Pipecat client wrapper (`lib/pipecat-client.ts`)
- ✅ Refactored hooks to use Pipecat SDK (`usePipecatClient.ts`)
- ✅ Updated UI components (ConnectionToggle, PTTButton)

### Backend Updates
- ✅ Added WebRTC transport handler (`transports/webrtc_transport.py`)
- ✅ Added WebRTC endpoints (`/api/webrtc/offer`, `/api/webrtc/ice-candidate`)
- ✅ Integrated SmallWebRTC transport from Pipecat

---

## 🚀 Installation Steps

### 1. Backend Setup

```bash
cd backend

# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Initialize Pipecat submodule
git submodule update --init --recursive

# Install dependencies
poetry install
poetry run pip install -e ./pipecat

# Configure environment
cp .env.example .env
# Edit .env and add your API keys:
# - OPENAI_API_KEY=your_key
# - OPENROUTER_API_KEY=your_key

# Run backend server
poetry run dev
# OR using make
make dev
```

Backend will start on `http://localhost:8000`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with backend URL:
# NEXT_PUBLIC_API_URL=http://localhost:8000

# Run development server
npm run dev
```

Frontend will start on `http://localhost:3000`

---

## 📝 Key Changes Explained

### 1. **Pipecat Client Integration**

The frontend now uses the official Pipecat client SDK:

```typescript
// lib/pipecat-client.ts
import { PipecatClient } from '@pipecat-ai/client-js'
import { SmallWebRTCTransport } from '@pipecat-ai/small-webrtc-transport'

// Creates WebRTC connection to backend
const client = new PipecatClient({
  transport: new SmallWebRTCTransport({
    baseUrl: API_URL,
    sessionId: sessionId,
  })
})
```

### 2. **New Hook: usePipecatClient**

Replaces the custom WebSocket implementation:

```typescript
// hooks/usePipecatClient.ts
const { connect, disconnect, sendPTTPress, sendPTTRelease } = usePipecatClient()

// Connect to session
await connect(sessionId)

// Send PTT events
sendPTTPress()  // User speaking
sendPTTRelease()  // User stopped
```

### 3. **Backend WebRTC Support**

Added SmallWebRTC transport endpoints:

```python
# POST /api/webrtc/offer
# - Client sends SDP offer
# - Backend returns SDP answer

# POST /api/webrtc/ice-candidate
# - Client sends ICE candidates
# - Backend processes for NAT traversal
```

---

## 🔧 Architecture Flow

### Connection Flow

```
1. Frontend → POST /api/session/create
   ← Backend: session_id

2. Frontend → Creates PipecatClient with SmallWebRTCTransport

3. Frontend → POST /api/webrtc/offer (SDP offer)
   ← Backend: SDP answer

4. Frontend ↔ Backend: ICE candidates exchange

5. Frontend ↔ Backend: WebRTC connection established
   - Bidirectional audio streaming
   - Data channel for messages (PTT, translations, etc.)
```

### PTT Workflow

**User Turn (PTT Pressed):**
```
Frontend: Hold button
→ sendPTTPress()
→ WebRTC data channel: {type: 'ptt_state', state: 'pressed'}
→ Backend: Switch to USER_SPEAKING state
→ User speaks into mic
→ Backend: STT → Translation → TTS
→ WebRTC audio stream: Translated audio
Frontend: Play audio, display home language text (right side)
```

**Partner Turn (PTT Released):**
```
Frontend: Release button
→ sendPTTRelease()
→ WebRTC data channel: {type: 'ptt_state', state: 'released'}
→ Backend: Switch to PARTNER_LISTENING state (VAD active)
→ Partner speaks
→ Backend: VAD → STT → Translation
→ WebRTC data channel: Translated text
Frontend: Display translated text (left side), NO audio
```

---

## 🧪 Testing the Setup

### 1. Test npm install

```bash
cd frontend
npm install
# Should succeed without errors
```

### 2. Test Backend Health

```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy", ...}
```

### 3. Test Session Creation

```bash
curl -X POST http://localhost:8000/api/session/create \
  -H "Content-Type: application/json" \
  -d '{"home_language":"en","target_language":"es"}'
# Should return session_id
```

### 4. Test Full Flow

1. Open `http://localhost:3000` in Chrome/Safari
2. Click "CONNECT" button
3. Allow microphone permissions
4. Hold PTT button and speak
5. Release button
6. Verify:
   - Your text appears on right (cyan)
   - Translation plays as audio
   - Partner text appears on left (magenta)

---

## 🐛 Troubleshooting

### "Package @pipecat-ai/client-js not found"

**Solution:** The package exists now! Run:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### "WebRTC connection failed"

**Possible causes:**
1. Backend not running on port 8000
2. CORS issues - check `ALLOWED_ORIGINS` in backend `.env`
3. Firewall blocking WebRTC ports

**Check:**
```bash
# Backend logs should show:
# "WebRTC offer processed for session: ..."

# Frontend console should show:
# "Pipecat client connected"
```

### "Pipecat import errors" (Backend)

**Solution:**
```bash
cd backend
poetry run pip install -e ./pipecat
```

### "Microphone permission denied"

**Solutions:**
- iOS Safari: Settings → Safari → Microphone → Allow
- Chrome: Site Settings → Microphone → Allow
- Must use HTTPS in production (localhost:3000 is OK for dev)

---

## 📦 Package Versions

### Frontend
- `@pipecat-ai/client-js`: `^1.5.0` ✅
- `@pipecat-ai/small-webrtc-transport`: `^1.0.0` ✅
- `next`: `^14.2.0`
- `react`: `^18.3.0`
- `zustand`: `^4.5.0`

### Backend (Poetry)
- `python`: `^3.10`
- `fastapi`: `^0.109.0`
- `pipecat-ai`: (from submodule)
- `openai`: `^1.10.0`
- `httpx`: `^0.26.0`

---

## 🎯 Next Steps

1. **Test on mobile devices:**
   - Use ngrok to expose localhost: `ngrok http 3000`
   - Access from mobile browser
   - Test PWA installation

2. **Production deployment:**
   - Deploy backend to cloud (AWS ECS, Google Cloud Run)
   - Deploy frontend to Vercel/Netlify
   - Configure TURN server for WebRTC NAT traversal

3. **Add features:**
   - Voice cloning
   - Conversation history
   - Multi-language support
   - Offline mode

---

## 📚 Documentation

- [Pipecat Docs](https://docs.pipecat.ai)
- [Pipecat Client SDK](https://docs.pipecat.ai/client/js/introduction)
- [SmallWebRTC Transport](https://github.com/pipecat-ai/pipecat-client-web-transports)
- [Project PRD](./docs/prd.md)
- [Implementation Plan](./docs/implementation-plan.md)

---

## ✅ Summary

The app now uses the **official Pipecat client SDK** with **SmallWebRTC transport** for real-time, low-latency voice translation. The npm install error has been fixed by updating to the correct package versions.

**Installation is now as simple as:**
```bash
# Backend
cd backend && make install && make dev

# Frontend (new terminal)
cd frontend && npm install && npm run dev
```

Enjoy building with Nebula Translate! 🌐✨
