# Nebula Translate - Comprehensive Implementation Plan

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Technology Stack](#technology-stack)
3. [Backend Implementation](#backend-implementation)
4. [Frontend Implementation](#frontend-implementation)
5. [Integration Strategy](#integration-strategy)
6. [Deployment Strategy](#deployment-strategy)
7. [Development Phases](#development-phases)

---

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Next.js Frontend                         │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │ PTT Button │  │ Audio Visual │  │   Chat Feed      │    │
│  └────────────┘  └──────────────┘  └──────────────────┘    │
│         │                 │                    ▲             │
│         └─────────────────┴────────────────────┘             │
│                          │                                   │
│                 WebRTC/WebSocket                             │
└─────────────────────────┼───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Python Backend (Pipecat)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Pipecat Pipeline Framework              │   │
│  │  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────┐  │   │
│  │  │   VAD   │→ │ STT (W) │→ │Translation│→ │ TTS  │  │   │
│  │  │ Silero  │  │ Whisper │  │ OpenRouter│  │OpenAI│  │   │
│  │  └─────────┘  └─────────┘  └──────────┘  └──────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
│                 WebRTC Transport Layer                       │
└─────────────────────────┼───────────────────────────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │   External Services    │
              │  - OpenAI (STT/TTS)   │
              │  - OpenRouter (LLM)   │
              └────────────────────────┘
```

### Core Design Principles

1. **Mobile-Only First**: Designed exclusively for mobile devices (smartphones). No desktop version. Optimized for touch, portrait orientation, and mobile browsers (iOS Safari, Android Chrome)
2. **Pipecat as Foundation**: All audio processing, VAD, and service orchestration runs through Pipecat's frame-based pipeline system
3. **Backend State Authority**: Backend manages all state transitions; frontend sends events and displays results
4. **Strict PTT Logic**: Push-to-Talk state always overrides automatic voice detection
5. **Bidirectional Translation**: Same pipeline handles both User→Partner and Partner→User flows
6. **Real-time First**: WebRTC for production, optimized for <500ms latency on mobile networks

---

## Technology Stack

### Backend (Python)
- **Framework**: Pipecat (voice agent orchestration)
- **Web Server**: FastAPI (WebSocket/REST endpoints)
- **Transport**: Pipecat WebRTC Transport (production) / WebSocket (development)
- **STT**: OpenAI Whisper API via Pipecat integration
- **TTS**: OpenAI TTS API via Pipecat integration
- **Translation**: OpenRouter API (GPT-4, Claude, etc.)
- **VAD**: Silero VAD via Pipecat
- **Environment**: Python 3.10+, asyncio

### Frontend (Next.js - Mobile-Only)
- **Framework**: Next.js 14+ (App Router) - Mobile-optimized PWA
- **UI**: React 18+ with TypeScript
- **State Management**: Zustand
- **WebRTC Client**: @pipecat-ai/client-js
- **Audio Processing**: Web Audio API (AudioWorklet)
- **Styling**: Tailwind CSS + custom cyberpunk theme
- **Build**: Turbopack
- **Mobile Features**:
  - PWA (Progressive Web App) with installability
  - Touch gesture optimization (hold, swipe, haptics)
  - Mobile viewport optimization (portrait-first)
  - iOS Safari & Android Chrome specific optimizations
  - Screen wake lock (prevent screen sleep during use)
  - Mobile microphone/speaker permissions handling
  - Responsive touch targets (min 44x44px)

### Infrastructure
- **Backend Deployment**: Docker containers (AWS ECS / Google Cloud Run)
- **Frontend Deployment**: Vercel / Netlify
- **WebRTC TURN/STUN**: Twilio / Cloudflare
- **Environment Secrets**: Managed via cloud provider secrets

---

## Backend Implementation

### Project Structure

```
backend/
├── main.py                      # FastAPI entry point
├── config.py                    # Configuration & environment vars
├── requirements.txt
├── Dockerfile
├── core/
│   ├── pipeline_manager.py      # Pipecat pipeline orchestrator
│   ├── session_manager.py       # Session lifecycle management
│   └── state_machine.py         # PTT state machine logic
├── services/
│   ├── stt_service.py           # OpenAI Whisper integration
│   ├── tts_service.py           # OpenAI TTS integration
│   ├── translation_service.py   # OpenRouter LLM translation
│   └── vad_service.py           # Silero VAD configuration
├── transports/
│   ├── webrtc_transport.py      # Production WebRTC handler
│   └── websocket_transport.py   # Development WebSocket handler
├── models/
│   ├── session.py               # Session data models
│   ├── messages.py              # Message schemas
│   └── enums.py                 # Language codes, states, etc.
└── utils/
    ├── audio_utils.py           # Audio format conversions
    └── logger.py                # Structured logging
```

### Core Components

#### 1. Pipecat Pipeline Manager

**Responsibilities:**
- Initialize Pipecat pipeline with frame processors
- Route audio frames based on PTT state
- Orchestrate STT → Translation → TTS flow
- Handle frame transformations and buffering

**Key Pipeline Flows:**

**User Turn (PTT Pressed)**:
```
AudioInputFrame → [VAD Disabled] → STT Processor → Translation Processor → TTS Processor → AudioOutputFrame
                                                                                        → TextFrame (chat display)
```

**Partner Turn (PTT Released)**:
```
AudioInputFrame → VAD Analyzer → STT Processor → Translation Processor → TextFrame (chat display only)
```

#### 2. State Machine

**States:**
- `DISCONNECTED`: No active session
- `CONNECTED`: Session established, idle
- `USER_SPEAKING`: PTT pressed, User talking
- `USER_PROCESSING`: User finished, translation in progress
- `PARTNER_LISTENING`: PTT released, VAD active
- `PARTNER_PROCESSING`: Partner speech detected, processing

**Transitions:**
- PTT Press → Force `USER_SPEAKING` (override any current state)
- PTT Release → Transition to `PARTNER_LISTENING` (enable VAD)
- VAD Start → `PARTNER_PROCESSING`
- Processing Complete → Return to `CONNECTED` or `PARTNER_LISTENING`

#### 3. Service Integrations

**STT Service (OpenAI Whisper)**
- Use Pipecat's OpenAI service integration
- Configure for real-time streaming transcription
- Language detection disabled (use session language config)
- Handle partial results for responsive feedback

**TTS Service (OpenAI TTS)**
- Use Pipecat's OpenAI TTS service
- Voice selection based on target language
- Stream audio chunks for low latency
- Only activated during User turn

**Translation Service (OpenRouter)**
- Custom Pipecat processor for LLM translation
- System prompt: Context-aware translation with tone preservation
- Support multiple models (GPT-4, Claude 3.5 Sonnet, etc.)
- Implement retry logic and fallback models

**VAD Service (Silero)**
- Configure Silero VAD analyzer
- Parameters from PRD: confidence (0.7), start_secs (0.2), stop_secs (0.8)
- Only active during Partner turn
- Emit events for speech start/stop

#### 4. WebRTC Transport

**Features:**
- Bidirectional audio streaming
- Data channel for control messages and text results
- Session signaling via FastAPI endpoints
- ICE candidate exchange
- STUN/TURN server configuration

**API Endpoints:**
```
POST   /api/session/create      # Initialize new session
POST   /api/session/connect     # WebRTC offer/answer exchange
DELETE /api/session/{id}        # Cleanup session
WS     /ws/session/{id}         # WebSocket fallback for development
```

---

## Frontend Implementation

### Project Structure

```
frontend/
├── app/
│   ├── page.tsx                 # Main translator interface (mobile-only)
│   ├── layout.tsx               # Root layout with viewport config
│   ├── manifest.ts              # PWA manifest configuration
│   └── api/                     # API route handlers (if needed)
├── components/
│   ├── ui/
│   │   ├── ConnectionToggle.tsx # Power button with states
│   │   ├── PTTButton.tsx        # Push-to-talk button (touch-optimized)
│   │   ├── AudioVisualizer.tsx  # Real-time waveform
│   │   ├── ThinkingIndicator.tsx# Processing animation
│   │   └── SettingsPanel.tsx    # Language config modal (fullscreen)
│   ├── chat/
│   │   ├── ChatFeed.tsx         # Message list container (mobile scroll)
│   │   ├── UserMessage.tsx      # Right-aligned user bubble
│   │   └── PartnerMessage.tsx   # Left-aligned partner bubble
│   └── layout/
│       └── MainLayout.tsx       # Core app layout (portrait-optimized)
├── lib/
│   ├── pipecat-client.ts        # Pipecat WebRTC client wrapper
│   ├── audio-processor.ts       # AudioWorklet for visualization
│   ├── session-api.ts           # Backend API calls
│   ├── types.ts                 # TypeScript interfaces
│   ├── mobile-utils.ts          # Mobile-specific utilities
│   └── pwa-utils.ts             # PWA installation & wake lock
├── store/
│   ├── translator-store.ts      # Zustand state management
│   └── settings-store.ts        # User preferences (localStorage)
├── hooks/
│   ├── usePTT.ts               # PTT button logic (touch + haptics)
│   ├── useAudioVisualization.ts # Waveform rendering
│   ├── useWebRTC.ts            # WebRTC connection management
│   ├── useWakeLock.ts          # Screen wake lock hook
│   └── useMobilePermissions.ts # Mic/speaker permission handling
├── styles/
│   ├── globals.css             # Mobile-first base styles
│   └── theme.ts                # Cyberpunk design tokens
└── public/
    ├── audio-worklet.js        # Web Audio processor
    ├── icons/                  # PWA icons (multiple sizes)
    │   ├── icon-192.png
    │   ├── icon-512.png
    │   └── apple-touch-icon.png
    └── manifest.json           # PWA manifest
```

### Key Components

#### 1. Connection Toggle

**States:**
- Disconnected: Gray/muted, "CONNECT" label
- Connecting: Pulsing animation, "CONNECTING..."
- Connected: Cyan accent, "CONNECTED", animated border

**Behavior:**
- Click to initiate WebRTC connection
- Show connection status and errors
- Cleanup session on disconnect

#### 2. PTT Button (Mobile-Optimized)

**Design:**
- Large circular button (min 250px diameter for easy thumb access)
- Positioned in bottom third of screen for one-handed use
- Touch target exceeds 44x44px minimum (iOS guideline)
- Visual states:
  - Idle: Border outline, "HOLD TO SPEAK"
  - Pressed: Filled background, "SPEAKING...", ripple animation
  - Processing: Pulsing border, "PROCESSING..."
- Anti-slip design: visual ring around edge for grip feedback

**Mobile-Specific Behavior:**
- `touchstart` event → Press event to backend + haptic feedback
- `touchend` event → Release event to backend
- `touchcancel` event → Emergency release (handle interruptions)
- Prevent scroll, zoom, and context menu during press
- Vibration API: Short pulse on press, double pulse on release
- Visual feedback starts immediately (<16ms) before network round-trip
- Lock orientation to portrait during active session
- Prevent accidental touches with debouncing

**iOS Safari Specifics:**
- Handle audio context unlock on first user interaction
- Manage silent mode detection
- Request microphone permission with clear messaging

**Android Chrome Specifics:**
- Wake lock during active session
- Handle background tab audio policies

#### 3. Audio Visualizer

**Implementation:**
- Canvas-based real-time bars (40-60 bars)
- Use Web Audio API AnalyserNode for frequency data
- Color coding:
  - User speaking: Cyan/accent color
  - Partner speaking: Magenta/secondary color
- Smoothed animation (60fps target)
- Amplitude normalization

#### 4. Thinking Indicator

**Trigger Conditions:**
- Audio input detected (amplitude threshold met)
- Waiting for STT/Translation/TTS response
- Network latency compensation

**Visual:**
- Overlay on visualizer area
- "NEBULA IS THINKING..." text
- Animated dots or spinner
- Semi-transparent backdrop

#### 5. Chat Feed

**Layout:**
- Vertical scroll container
- Auto-scroll to newest message
- Max height with overflow scroll
- Timestamp for each message

**User Messages (Right Aligned):**
- Cyan border/glow effect
- Contains Home Language text
- Label: "YOU ({HOME_LANG})"
- Background: Dark with accent

**Partner Messages (Left Aligned):**
- Magenta subtle background
- Contains translated Home Language text
- Label: "PARTNER (TRANSLATION)"
- Muted styling

#### 6. Settings Panel

**Configuration:**
- Home Language selector (dropdown with search)
- Target Language selector
- Voice selection (for TTS output)
- Audio input/output device selection
- Save preferences to localStorage

### Mobile-Specific Considerations

#### 1. PWA (Progressive Web App) Setup

**Features:**
- Installable to home screen (iOS & Android)
- Standalone display mode (fullscreen, no browser UI)
- Custom splash screen with cyberpunk branding
- Offline fallback page for network errors
- App icon sizes: 192x192, 512x512, apple-touch-icon

**Manifest Configuration:**
```json
{
  "name": "Nebula Translate",
  "short_name": "Nebula",
  "display": "standalone",
  "orientation": "portrait",
  "theme_color": "#0a0a0f",
  "background_color": "#0a0a0f",
  "start_url": "/",
  "scope": "/"
}
```

**Installation Prompt:**
- Detect if app is installable
- Show custom "Add to Home Screen" prompt after first successful translation
- Defer browser's default install prompt
- Track installation analytics

#### 2. Mobile Performance Optimizations

**Battery Conservation:**
- Reduce animation frame rate when battery is low (Battery API)
- Pause audio visualizer when in background
- Implement connection timeout for idle sessions (5 minutes)
- Clean up WebRTC connections aggressively

**Network Optimization:**
- Adaptive quality based on connection type (4G, 5G, WiFi)
- Reduce audio bitrate on slow connections
- Show network quality indicator
- Offline detection and graceful degradation
- Implement retry with exponential backoff for mobile network instability

**Memory Management:**
- Limit chat history to last 50 messages
- Clear old audio buffers proactively
- Lazy load components below the fold
- Use React.memo for expensive components

#### 3. Touch Gesture Optimization

**Implemented Gestures:**
- Long press PTT button (primary interaction)
- Pull down to refresh connection
- Swipe up to open settings
- Double tap to clear chat (with confirmation)
- Pinch to zoom text (accessibility)

**Touch Feedback:**
- 10ms haptic feedback on all touch interactions
- Visual ripple effects for button presses
- Disabled 300ms click delay (touch-action CSS)
- Prevent double-tap zoom on critical UI elements

#### 4. Viewport & Layout

**Configuration:**
```html
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
```

**Safe Area Handling:**
- CSS env() variables for notch/home indicator on iOS
- Padding for safe areas on iPhone X+ models
- Bottom navigation positioned above home indicator
- Account for on-screen keyboards (resize viewport)

**Layout Structure:**
- Top: Connection status + language indicators (60px)
- Middle: Chat feed (flexible, scrollable)
- Center: Audio visualizer (80px)
- Bottom: PTT button + safe area padding (300px)

#### 5. Audio Handling on Mobile

**iOS Safari Audio Challenges:**
- Unlock AudioContext on first user gesture
- Request microphone permission before connection
- Handle "silent mode" detection (no speaker output warning)
- Work around iOS audio autoplay restrictions
- Use WebRTC for bidirectional audio (bypass Web Audio limitations)

**Android Chrome Audio:**
- Request microphone permission with rationale
- Handle Bluetooth headset switching
- Manage audio routing (speaker vs earpiece)
- Background audio continuation support

**General Audio:**
- Monitor audio input levels for silence detection
- Auto-gain control for microphone input
- Echo cancellation enabled by default
- Noise suppression for better transcription

#### 6. Mobile Browser Compatibility

**Target Browsers:**
- iOS Safari 15+ (primary)
- Android Chrome 100+ (primary)
- Samsung Internet (secondary)
- Firefox Mobile (best-effort)

**Progressive Enhancement:**
- Core functionality works without PWA features
- Fallback UI for browsers without wake lock API
- Polyfills for missing Web APIs (minimal)
- Feature detection, not browser detection

#### 7. Accessibility on Mobile

**Touch Accessibility:**
- Minimum touch target size: 48x48px
- Sufficient spacing between interactive elements (8px minimum)
- Visual focus indicators for keyboard navigation (external keyboard)
- High contrast mode support

**Screen Reader Support:**
- ARIA labels for all interactive elements
- Live regions for dynamic content (new messages)
- Announce connection state changes
- Semantic HTML structure

**Text Accessibility:**
- Support system font scaling (up to 200%)
- Minimum font size: 16px (prevents iOS zoom on input focus)
- High contrast text (WCAG AAA for cyberpunk theme)
- Option to increase chat message font size in settings

### State Management (Zustand)

```typescript
interface TranslatorState {
  // Connection
  connectionState: 'disconnected' | 'connecting' | 'connected'
  sessionId: string | null

  // PTT State
  isPTTPressed: boolean
  currentSpeaker: 'user' | 'partner' | null

  // Processing
  isProcessing: boolean
  processingStage: 'stt' | 'translation' | 'tts' | null

  // Messages
  messages: Message[]

  // Config
  homeLanguage: string
  targetLanguage: string

  // Audio
  audioLevel: number

  // Actions
  setConnectionState: (state) => void
  setPTTPressed: (pressed: boolean) => void
  addMessage: (message: Message) => void
  updateLanguages: (home: string, target: string) => void
}
```

### WebRTC Client Integration

**Initialization:**
- Import `@pipecat-ai/client-js`
- Create RTCPeerConnection with STUN/TURN config
- Set up media stream from microphone
- Establish data channel for control messages

**Event Handling:**
- PTT press/release → Send via data channel
- Incoming audio → Play through AudioContext
- Incoming messages → Update Zustand store
- Connection state changes → Update UI

### Mobile Implementation Details

#### 1. Next.js Configuration for Mobile PWA

**next.config.js:**
```javascript
module.exports = {
  // PWA configuration
  experimental: {
    webVitalsAttribution: ['CLS', 'LCP']
  },
  // Optimize for mobile
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production'
  },
  // Headers for mobile
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-DNS-Prefetch-Control', value: 'on' },
          { key: 'Permissions-Policy', value: 'microphone=*' }
        ]
      }
    ]
  }
}
```

**Root Layout (layout.tsx):**
```typescript
export const viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: 'cover',
  themeColor: '#0a0a0f'
}

export const metadata = {
  title: 'Nebula Translate',
  description: 'Real-time AI translation',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'Nebula'
  }
}
```

#### 2. PWA Service Worker Strategy

**Use next-pwa or Workbox:**
- Cache-first for static assets (JS, CSS, fonts)
- Network-first for API calls (with timeout)
- Offline fallback page when backend unreachable
- Skip waiting for immediate updates
- Clean old caches automatically

**Precache Strategy:**
```javascript
// Precache critical resources
[
  '/',
  '/audio-worklet.js',
  '/icons/icon-192.png',
  '/manifest.json'
]
```

#### 3. Touch Event Implementation

**PTT Button Touch Handler:**
```typescript
const handleTouchStart = (e: TouchEvent) => {
  e.preventDefault(); // Prevent scroll, zoom
  navigator.vibrate?.(10); // Haptic feedback
  setPTTPressed(true);
  sendPTTState('pressed');
}

const handleTouchEnd = (e: TouchEvent) => {
  e.preventDefault();
  navigator.vibrate?.([10, 50, 10]); // Double pulse
  setPTTPressed(false);
  sendPTTState('released');
}

// Handle interruptions (phone call, notification)
const handleTouchCancel = (e: TouchEvent) => {
  setPTTPressed(false);
  sendPTTState('released');
}
```

**CSS Touch Optimization:**
```css
.ptt-button {
  touch-action: none; /* Disable default touch behaviors */
  -webkit-tap-highlight-color: transparent;
  user-select: none;
  -webkit-user-select: none;
}
```

#### 4. Screen Wake Lock Implementation

**useWakeLock Hook:**
```typescript
const useWakeLock = (isActive: boolean) => {
  useEffect(() => {
    let wakeLock: WakeLockSentinel | null = null;

    const requestWakeLock = async () => {
      try {
        if ('wakeLock' in navigator && isActive) {
          wakeLock = await navigator.wakeLock.request('screen');
        }
      } catch (err) {
        console.warn('Wake Lock failed:', err);
      }
    }

    requestWakeLock();

    return () => {
      wakeLock?.release();
    }
  }, [isActive]);
}
```

#### 5. Mobile Audio Context Unlocking

**iOS Safari AudioContext Unlock:**
```typescript
const unlockAudioContext = async (audioContext: AudioContext) => {
  if (audioContext.state === 'suspended') {
    // Create silent buffer and play on user gesture
    const buffer = audioContext.createBuffer(1, 1, 22050);
    const source = audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(audioContext.destination);
    source.start(0);

    await audioContext.resume();
  }
}

// Call on first user interaction (connection button tap)
```

#### 6. Mobile Permission Handling

**Microphone Permission Request:**
```typescript
const requestMicrophonePermission = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    });

    // Store stream for later use
    setMediaStream(stream);
    return true;
  } catch (err) {
    if (err.name === 'NotAllowedError') {
      // Show permission denied UI
      showPermissionDeniedModal();
    }
    return false;
  }
}
```

#### 7. Viewport Height Fix for Mobile Browsers

**Handle iOS Safari address bar:**
```typescript
// Fix for 100vh on mobile (address bar changes height)
const setViewportHeight = () => {
  const vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
}

window.addEventListener('resize', setViewportHeight);
window.addEventListener('orientationchange', setViewportHeight);
setViewportHeight();
```

**CSS:**
```css
.full-height {
  height: 100vh; /* Fallback */
  height: calc(var(--vh, 1vh) * 100);
}
```

#### 8. Network Quality Detection

**Adaptive Quality Based on Connection:**
```typescript
const useNetworkQuality = () => {
  const [quality, setQuality] = useState<'high' | 'medium' | 'low'>('high');

  useEffect(() => {
    const connection = (navigator as any).connection;
    if (!connection) return;

    const updateQuality = () => {
      const effectiveType = connection.effectiveType;
      if (effectiveType === '4g' || effectiveType === 'wifi') {
        setQuality('high');
      } else if (effectiveType === '3g') {
        setQuality('medium');
      } else {
        setQuality('low');
      }
    }

    connection.addEventListener('change', updateQuality);
    updateQuality();

    return () => connection.removeEventListener('change', updateQuality);
  }, []);

  return quality;
}
```

#### 9. iOS Safe Area Handling

**CSS for Notch/Home Indicator:**
```css
.app-container {
  padding-top: env(safe-area-inset-top);
  padding-bottom: env(safe-area-inset-bottom);
  padding-left: env(safe-area-inset-left);
  padding-right: env(safe-area-inset-right);
}

.ptt-button-container {
  /* Position above home indicator on iPhone X+ */
  padding-bottom: max(20px, env(safe-area-inset-bottom));
}
```

---

## Integration Strategy

### 1. Audio Pipeline Flow

**User Turn Complete Flow:**
```
1. User presses PTT button
   → Frontend sends {type: 'ptt', state: 'pressed'} via data channel

2. Backend switches to USER_SPEAKING state
   → Disables VAD, routes to User pipeline

3. User speaks into microphone
   → Audio frames sent via WebRTC audio track

4. Backend processes audio through pipeline:
   → STT (Whisper): Transcribe to Home Language text
   → Translation (OpenRouter): Translate Home → Target Language
   → TTS (OpenAI): Synthesize Target Language audio

5. Backend sends results:
   → Audio frames back via WebRTC (Partner hears translation)
   → Text message via data channel: {type: 'message', side: 'user', text: homeLanguageText}

6. Frontend receives and displays:
   → User message bubble (right, Home Language)
   → Plays audio output automatically

7. User releases PTT button
   → Backend switches to PARTNER_LISTENING state
```

**Partner Turn Complete Flow:**
```
1. PTT button released (default state)
   → Backend VAD is active, listening

2. Partner speaks
   → VAD detects speech start
   → Backend switches to PARTNER_PROCESSING

3. Backend processes audio:
   → STT (Whisper): Transcribe to Target Language
   → Translation (OpenRouter): Translate Target → Home Language
   → [NO TTS - silent mode]

4. Backend sends result via data channel:
   → {type: 'message', side: 'partner', text: translatedHomeLanguageText}

5. Frontend displays:
   → Partner message bubble (left, translated to Home Language)
   → User reads the translation

6. VAD detects speech end
   → Backend returns to PARTNER_LISTENING state
```

### 2. Error Handling

**Network Errors:**
- WebRTC connection loss → Show reconnection UI
- Retry logic with exponential backoff
- Graceful degradation to WebSocket if WebRTC fails

**API Errors:**
- STT failure → Display "Could not transcribe audio"
- Translation failure → Show original text + error indicator
- TTS failure → Silent mode, show text only

**User Experience:**
- All errors shown in non-intrusive toast notifications
- Critical errors (connection loss) shown in modal
- Preserve session state during reconnection

### 3. Performance Optimization

**Latency Targets:**
- User turn total (speech → translated audio output): <2 seconds
- Partner turn total (speech → translated text display): <1.5 seconds

**Optimization Techniques:**
- Stream partial STT results for faster perceived response
- Use streaming translation for long utterances
- Pre-buffer TTS audio chunks
- Minimize frame processing overhead in Pipecat
- WebRTC audio codec optimization (Opus preferred)

---

## Deployment Strategy

### Backend Deployment

**Containerization (Dockerfile):**
```dockerfile
FROM python:3.10-slim
# Install system dependencies for audio processing
# Copy requirements and install Python packages
# Copy application code
# Expose ports for FastAPI and WebRTC
# Set entrypoint for uvicorn server
```

**Environment Variables:**
```
OPENAI_API_KEY=         # For Whisper STT and TTS
OPENROUTER_API_KEY=     # For LLM translation
TURN_SERVER_URL=        # TURN server for WebRTC NAT traversal
TURN_USERNAME=
TURN_CREDENTIAL=
ALLOWED_ORIGINS=        # CORS for frontend domain
LOG_LEVEL=INFO
```

**Infrastructure:**
- Deploy to AWS ECS, Google Cloud Run, or similar
- Auto-scaling based on CPU/memory
- Health check endpoint: `GET /health`
- Logging to CloudWatch / Stackdriver

### Frontend Deployment (Mobile PWA)

**Vercel/Netlify Configuration:**
- Automatic deployment on git push
- Environment variables for backend API URL
- Edge functions for session management (optional)
- CDN for static assets
- HTTPS enforced (required for PWA and WebRTC)
- Custom domain for better PWA installation UX

**PWA Build Configuration:**
- Generate service worker with Workbox
- Cache static assets for offline fallback
- Runtime caching for API responses
- Background sync for analytics (optional)
- Push notification setup (future feature)

**Mobile Build Optimization:**
- Tree-shaking for minimal bundle size (<200KB target)
- Code splitting by route
- Lazy load non-critical components
- Preload critical audio resources
- Image optimization (WebP, compression)
- Font subsetting for cyberpunk theme
- Remove source maps in production
- Aggressive minification for mobile networks

**Mobile-Specific Headers:**
```
X-UA-Compatible: IE=edge (not needed for mobile, but safe)
Content-Security-Policy: Strict for XSS protection
Permissions-Policy: microphone=*, camera=()
```

### Security Considerations

1. **API Keys**: Never expose in frontend, backend only
2. **CORS**: Strict origin allowlist for production
3. **Rate Limiting**: Prevent abuse of STT/TTS/Translation APIs
4. **Session Validation**: Authenticate WebRTC connections
5. **Input Sanitization**: Validate language codes and user inputs

---

## Development Phases

### Phase 1: Backend Foundation (Week 1-2)
- Set up Python project with Pipecat
- Implement basic WebSocket transport for development
- Create session manager and state machine
- Integrate OpenAI Whisper STT service
- Test audio transcription pipeline

### Phase 2: Translation & TTS (Week 2-3)
- Integrate OpenRouter for LLM translation
- Test translation quality with different models
- Integrate OpenAI TTS service
- Implement User turn complete pipeline (STT → Translation → TTS)
- Add Silero VAD for Partner turn detection

### Phase 3: Frontend Core (Week 3-4)
- Set up Next.js project with Tailwind
- Create basic layout and components
- Implement Zustand state management
- Build PTT button with touch support
- Create chat feed with message display

### Phase 4: WebRTC Integration (Week 4-5)
- Integrate Pipecat client library
- Implement WebRTC connection flow
- Test bidirectional audio streaming
- Add data channel for control messages
- Test PTT state synchronization

### Phase 5: UI Polish & Features (Week 5-6)
- Implement cyberpunk theme (colors, typography, animations)
- Build audio visualizer with Web Audio API
- Add thinking/processing indicator
- Create settings panel for language config
- Implement connection toggle with states

### Phase 6: Mobile Testing & Optimization (Week 6-7)
- End-to-end testing of conversation flows on real devices
- Latency optimization for mobile networks (3G, 4G, 5G, WiFi)
- Error handling and edge cases (network drops, interruptions)
- **iOS Testing:**
  - iPhone SE, iPhone 12/13/14/15 (various screen sizes)
  - iPad (optional, portrait mode)
  - iOS Safari 15, 16, 17+
  - Test with silent mode on/off
  - Test with AirPods, Bluetooth headsets
- **Android Testing:**
  - Samsung Galaxy S20+, Pixel 6+
  - Various Android versions (11, 12, 13, 14)
  - Chrome, Samsung Internet
  - Test with wired/Bluetooth headphones
- PWA installation testing on both platforms
- Touch gesture testing (various screen sizes, one-handed use)
- Battery drain testing during extended sessions
- Network quality adaptation testing
- Screen wake lock verification

### Phase 7: Production Deployment (Week 7-8)
- Migrate from WebSocket to WebRTC transport
- Set up TURN/STUN servers
- Deploy backend to cloud (containerized)
- Deploy frontend to Vercel/Netlify
- Production testing with real network conditions
- Monitor logs and performance metrics

---

## Success Metrics

### Functional Requirements
- [x] PTT button press → User audio → Translated audio output
- [x] PTT button release → Partner audio → Translated text display
- [x] Bidirectional translation (Home ↔ Target)
- [x] Real-time audio visualization
- [x] Processing indicator during latency
- [x] Chat transcript with proper alignment

### Performance Requirements (Mobile-Specific)
- **Latency:**
  - User turn: <2s on 4G/WiFi, <3s on 3G
  - Partner turn: <1.5s on 4G/WiFi, <2.5s on 3G
  - PTT visual feedback: <16ms (one frame)
  - Network round-trip awareness and compensation
- **Audio Quality:**
  - Clear TTS output, minimal artifacts
  - Adaptive bitrate based on connection (Opus codec)
  - Echo cancellation and noise suppression enabled
- **UI Responsiveness:**
  - 60fps animations on modern devices (iPhone 11+, Android flagship)
  - 30fps fallback for older devices
  - Instant haptic/visual PTT feedback (<16ms)
  - Smooth scrolling in chat feed
- **Connection Stability:**
  - Auto-reconnect with exponential backoff
  - <1% drop rate on stable networks
  - Graceful handling of network switches (WiFi ↔ 4G)
  - Resume session state after brief disconnections
- **Bundle Size:**
  - Initial JS bundle: <200KB gzipped
  - Total page weight: <500KB
  - First Contentful Paint: <1.5s on 4G
  - Time to Interactive: <3s on 4G
- **Battery:**
  - <5% battery drain per 10-minute session
  - Reduce power consumption when backgrounded
  - Efficient WebRTC codec selection

### User Experience Requirements (Mobile-Only)
- **Touch Interaction:**
  - Intuitive PTT interaction (no confusion on who is speaking)
  - One-handed operation support
  - Large touch targets (min 48x48px)
  - Haptic feedback for all interactions
  - No accidental touches (proper debouncing)
- **Visual Design:**
  - Cyberpunk aesthetic matching PRD
  - Portrait-optimized layout
  - High contrast for outdoor visibility
  - Readable text in various lighting conditions
  - Smooth animations that feel native
- **Mobile UX:**
  - Works in standalone PWA mode (no browser chrome)
  - Handles phone calls gracefully (pause/resume)
  - Screen stays awake during active sessions
  - Notification for background disconnections (future)
  - Quick access from home screen (PWA install)
- **Accessibility:**
  - Screen reader support (VoiceOver, TalkBack)
  - Dynamic type/font scaling support
  - High contrast mode
  - Minimum 16px font size
  - Alternative to haptics for devices without vibration

---

## Future Enhancements

1. **Multi-language Support**: Support for 50+ languages beyond initial pair
2. **Conversation History**: Cloud storage of past sessions
3. **Voice Cloning**: Preserve user's voice characteristics in translation
4. **Offline Mode**: Local STT/TTS models for privacy
5. **Group Conversations**: Multi-party translation support
6. **Context Awareness**: Use conversation history for better translation
7. **Custom Vocabulary**: Industry-specific terminology support
8. **Analytics Dashboard**: Usage stats, latency metrics, error rates

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| API rate limits (OpenAI/OpenRouter) | High | Implement caching, use multiple API keys, fallback providers |
| WebRTC connection failures on mobile | High | Robust TURN server config, WebSocket fallback, auto-reconnect, handle network switches |
| iOS Safari audio restrictions | High | Unlock AudioContext early, clear permission prompts, comprehensive iOS testing |
| Translation quality issues | Medium | Support multiple LLM models, allow user feedback, manual correction |
| Audio latency > 2s on mobile networks | Medium | Optimize pipeline, adaptive bitrate, network-aware quality settings |
| Mobile browser compatibility | Medium | Focus on iOS Safari & Android Chrome, progressive enhancement, feature detection |
| Battery drain during extended use | Medium | Reduce animations when low battery, efficient WebRTC codec, timeout idle sessions |
| PWA installation friction | Medium | Custom install prompts, clear value proposition, defer until after first success |
| Small screen UI crowding | Low | Portrait-first design, collapsible sections, prioritize essential UI |
| Pipecat learning curve | Low | Use official docs, examples, community support |

---

## Conclusion

This implementation plan delivers a **mobile-first, mobile-only** real-time translation app optimized for face-to-face conversations on smartphones. The architecture leverages:

- **Pipecat** as the core orchestration framework for audio processing, VAD, and service integration
- **OpenAI** for high-quality STT (Whisper) and TTS
- **OpenRouter** for flexible, multi-model LLM translation
- **PWA** for native app-like experience with offline capabilities
- **WebRTC** for low-latency audio streaming optimized for mobile networks

The strict PTT-based workflow ensures clear turn-taking, while the cyberpunk UI provides an engaging, futuristic interpreter experience designed exclusively for mobile touch interfaces. Every aspect—from touch gestures and haptic feedback to battery optimization and iOS Safari audio handling—is built specifically for mobile devices.

**Key Mobile Advantages:**
- One-handed operation with large touch targets
- Works offline (PWA) with home screen installation
- Optimized for 3G/4G/5G mobile networks
- Battery-conscious design for extended sessions
- Native-feeling animations and interactions
- Handles phone calls and interruptions gracefully

This is not a responsive web app adapted for mobile—it's a mobile-native experience from the ground up.
