# Nebula Translate - Frontend

Mobile-first Progressive Web App (PWA) for real-time voice translation.

## Features

- **Mobile-Optimized UI**: Portrait-first design with touch gestures
- **PWA Support**: Install to home screen, offline capability
- **Cyberpunk Theme**: Dark mode with neon accents
- **Real-time Audio Visualization**: Color-coded waveforms
- **Haptic Feedback**: Vibration on interactions
- **Screen Wake Lock**: Prevents sleep during sessions

## Tech Stack

- Next.js 14 (App Router)
- React 18
- TypeScript
- Zustand (state management)
- Tailwind CSS
- Web Audio API

## Quick Start

```bash
# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your backend URL

# Run development server
npm run dev
```

Visit `http://localhost:3000`

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout with PWA config
│   ├── page.tsx            # Main translator interface
│   ├── globals.css         # Global styles
│   └── manifest.ts         # PWA manifest
├── components/
│   ├── ui/
│   │   ├── PTTButton.tsx           # Push-to-talk button
│   │   ├── AudioVisualizer.tsx     # Real-time waveform
│   │   ├── ConnectionToggle.tsx    # Connection button
│   │   ├── ThinkingIndicator.tsx   # Processing animation
│   │   └── SettingsPanel.tsx       # Language settings
│   ├── chat/
│   │   ├── ChatFeed.tsx           # Message list
│   │   ├── UserMessage.tsx        # User message bubble
│   │   └── PartnerMessage.tsx     # Partner message bubble
│   └── layout/
│       └── MainLayout.tsx         # App layout container
├── store/
│   ├── translator-store.ts   # Translation state
│   └── settings-store.ts      # User settings (persisted)
├── hooks/
│   ├── usePTT.ts             # PTT button logic
│   ├── usePipecatClient.ts   # WebRTC connection (Pipecat SDK)
│   └── useWakeLock.ts        # Screen wake lock
├── lib/
│   └── types.ts              # TypeScript definitions
└── public/
    ├── icons/                # PWA icons
    └── manifest.json         # PWA manifest
```

## Components

### PTTButton

Large, touch-optimized button for voice input.

**Features:**
- Touch event handling (start, end, cancel)
- Haptic feedback
- Visual state (idle, pressed, processing)
- Animated ring effect when active

**Usage:**
```tsx
<PTTButton disabled={!isConnected} />
```

### AudioVisualizer

Real-time audio level visualization with 50 bars.

**Features:**
- Canvas-based rendering (60fps)
- Color coding (cyan for user, magenta for partner)
- Responsive to audio input levels

**Usage:**
```tsx
<AudioVisualizer />
```

### ChatFeed

Scrollable message list with auto-scroll.

**Features:**
- User messages (right-aligned, cyan)
- Partner messages (left-aligned, magenta)
- Auto-scroll to latest message
- Timestamp display

**Usage:**
```tsx
<ChatFeed />
```

## State Management

### Translator Store

Global state for translation session:

```typescript
{
  connectionState: 'disconnected' | 'connecting' | 'connected',
  sessionId: string | null,
  isPTTPressed: boolean,
  currentSpeaker: 'user' | 'partner' | null,
  isProcessing: boolean,
  messages: Message[],
  homeLanguage: string,
  targetLanguage: string,
  audioLevel: number
}
```

### Settings Store

Persisted user preferences (localStorage):

```typescript
{
  homeLanguage: string,
  targetLanguage: string,
  isOpen: boolean
}
```

## Custom Hooks

### usePTT

Handles Push-to-Talk button interactions:

```typescript
const { isPTTPressed, handlers } = usePTT(onPressStart, onPressEnd)
```

Returns touch/mouse event handlers for PTT button.

### usePipecatClient

Manages WebRTC connection to backend using Pipecat SDK:

```typescript
const { connect, disconnect, sendPTTPress, sendPTTRelease } = usePipecatClient()
```

Handles:
- WebRTC peer connection via SmallWebRTC transport
- Real-time audio streaming (bidirectional)
- Data channel messages (translation text, audio levels, thinking indicator)
- Auto-reconnection with exponential backoff
- PTT state messaging

### useWakeLock

Prevents screen sleep during active sessions:

```typescript
useWakeLock(isConnected)
```

Automatically acquires/releases wake lock based on connection state.

## Mobile Optimizations

### Touch Handling

```typescript
// PTT button
onTouchStart   // Press
onTouchEnd     // Release
onTouchCancel  // Handle interruptions (phone calls, etc.)
```

### Haptic Feedback

```typescript
navigator.vibrate(10)         // Press
navigator.vibrate([10, 50, 10]) // Release (double pulse)
```

### Viewport Height Fix

Handles iOS Safari address bar:

```typescript
const vh = window.innerHeight * 0.01
document.documentElement.style.setProperty('--vh', `${vh}px`)
```

Use in CSS:
```css
.h-screen-dynamic {
  height: calc(var(--vh, 1vh) * 100);
}
```

### Safe Area Padding

For iPhone notch/home indicator:

```css
.safe-area-padding {
  padding-top: env(safe-area-inset-top);
  padding-bottom: env(safe-area-inset-bottom);
}
```

## PWA Configuration

### Manifest

Located at `app/manifest.ts`:

```typescript
{
  name: 'Nebula Translate',
  short_name: 'Nebula',
  display: 'standalone',
  orientation: 'portrait',
  theme_color: '#0a0a0f'
}
```

### Service Worker

Automatically generated by Next.js for static asset caching.

### Installation

iOS Safari:
1. Open in Safari
2. Tap Share button
3. "Add to Home Screen"

Android Chrome:
1. Open in Chrome
2. Tap menu (⋮)
3. "Install app"

## Styling

### Tailwind Configuration

Custom cyberpunk theme in `tailwind.config.ts`:

```typescript
colors: {
  'cyber-dark': '#0a0a0f',
  'cyber-cyan': '#00ffff',
  'cyber-magenta': '#ff00ff',
}
```

### Custom Classes

```css
.cyber-glow          /* Cyan glow effect */
.cyber-text-glow     /* Text shadow glow */
.no-select           /* Prevent text selection */
.touch-manipulation  /* Touch optimization */
.custom-scrollbar    /* Styled scrollbar */
```

## Environment Variables

```bash
NEXT_PUBLIC_API_URL   # Backend REST API URL
NEXT_PUBLIC_WS_URL    # Backend WebSocket URL
```

## Build & Deploy

### Development

```bash
npm run dev
```

### Production Build

```bash
npm run build
npm start
```

### Deploy to Vercel

```bash
vercel deploy --prod
```

## Testing

### Mobile Testing

1. Use Chrome DevTools Device Mode
2. Test on real devices:
   - iPhone (iOS Safari)
   - Android (Chrome)
3. Test touch gestures
4. Verify PWA installation
5. Check haptic feedback
6. Test screen wake lock

### Audio Testing

1. Verify microphone permission prompt
2. Test audio visualization
3. Check TTS audio playback
4. Test with headphones/Bluetooth

## Troubleshooting

### "Module not found" errors
```bash
rm -rf node_modules .next
npm install
```

### PWA not installing
- Must be served over HTTPS
- Use ngrok for local testing: `ngrok http 3000`

### Audio not playing on iOS
- Unlock AudioContext on user gesture
- Check silent mode switch
- Test with headphones

### Touch events not working
- Ensure `touch-action: none` CSS is applied
- Check for conflicting event listeners

## Performance

### Bundle Size

Target: <200KB initial JS bundle

Monitor with:
```bash
npm run build
# Check .next/static/ sizes
```

### Lighthouse Score

Mobile targets:
- Performance: >90
- Accessibility: >95
- Best Practices: >95
- PWA: 100

## License

Proprietary - Nebula Translate
