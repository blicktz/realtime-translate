/**
 * Pipecat Client SDK Wrapper for Nebula Translate
 *
 * This wrapper configures the Pipecat client with SmallWebRTC transport
 * for real-time voice translation.
 */

import { PipecatClient, RTVIEvent, RTVIMessage } from '@pipecat-ai/client-js'
import { SmallWebRTCTransport } from '@pipecat-ai/small-webrtc-transport'

export interface PipecatConfig {
  baseUrl: string
  sessionId: string
  enableMic?: boolean
  enableCam?: boolean
}

export interface PipecatCallbacks {
  onConnected?: () => void
  onDisconnected?: () => void
  onError?: (error: Error) => void
  onMessage?: (message: RTVIMessage) => void
  onServerMessage?: (message: RTVIMessage) => void  // Official callback for data channel messages
  onTranscript?: (text: string, speaker: 'user' | 'partner') => void
  onTranslation?: (text: string, speaker: 'user' | 'partner') => void
  onAudioLevel?: (level: number, speaker: 'user' | 'partner') => void
  onThinking?: (isThinking: boolean) => void
}

export class NebulaTranslateClient {
  private client: PipecatClient | null = null
  private transport: SmallWebRTCTransport | null = null
  private callbacks: PipecatCallbacks = {}

  constructor() {
    // Client will be initialized when connect() is called
  }

  /**
   * Initialize and connect to the Pipecat backend
   */
  async connect(config: PipecatConfig, callbacks: PipecatCallbacks = {}) {
    try {
      this.callbacks = callbacks

      // Create SmallWebRTC transport
      // Transport does not need baseUrl/sessionId - those are passed via connect() params
      this.transport = new SmallWebRTCTransport()

      // Create Pipecat client with transport
      // NOTE: enableMic/enableCam must be set at CLIENT level, not transport level
      this.client = new PipecatClient({
        transport: this.transport,
        enableMic: config.enableMic ?? true,
        enableCam: config.enableCam ?? false,
        callbacks: {
          // Official callback for receiving data channel messages from backend
          onServerMessage: (message: RTVIMessage) => {
            console.log('[CALLBACK] ✅ onServerMessage callback fired!')
            console.log('[CALLBACK] Message received:', JSON.stringify(message, null, 2))
            this.handleMessage(message)
            this.callbacks.onServerMessage?.(message)
          },
          // Add more callbacks to catch different message types
          onConnected: () => {
            console.log('[CALLBACK] onConnected fired')
            this.callbacks.onConnected?.()
          },
          onMessageError: (message: RTVIMessage) => {
            console.log('[CALLBACK] onMessageError fired:', message)
          }
        }
      })
      console.log('[Pipecat] Initialized client with config:', {
        enableMic: config.enableMic ?? true,
        enableCam: config.enableCam ?? false,
        sessionId: config.sessionId
      })

      // Register event handlers
      this.registerEventHandlers()

      // DEBUGGING: Log ALL events to catch everything (except noisy ones)
      console.log('[DEBUG] Registering catch-all event listeners...')
      const allEvents = Object.values(RTVIEvent)
      const noisyEvents = ['localAudioLevel', 'remoteAudioLevel'] // Filter out audio level spam
      allEvents.forEach((eventName) => {
        if (!noisyEvents.includes(eventName)) {
          this.client!.on(eventName as any, (...args: any[]) => {
            console.log(`[SDK-EVENT] ${eventName} fired with args:`, args)
          })
        }
      })

      // Connect to backend with WebRTC request parameters
      await this.client.connect({
        webrtcRequestParams: {
          endpoint: `${config.baseUrl}/api/webrtc/offer`,
          requestData: {
            session_id: config.sessionId
          }
        }
      })

      console.log('Pipecat client connected successfully')
      this.callbacks.onConnected?.()

    } catch (error) {
      console.error('Failed to connect Pipecat client:', error)
      this.callbacks.onError?.(error as Error)
      throw error
    }
  }

  /**
   * Disconnect from the backend
   */
  async disconnect() {
    try {
      if (this.client) {
        await this.client.disconnect()
        this.client = null
      }
      if (this.transport) {
        this.transport = null
      }

      console.log('Pipecat client disconnected')
      this.callbacks.onDisconnected?.()
    } catch (error) {
      console.error('Error disconnecting:', error)
      this.callbacks.onError?.(error as Error)
    }
  }

  /**
   * Send PTT press event
   */
  sendPTTPress() {
    this.sendMessage({
      type: 'ptt_state',
      state: 'pressed',
    })
  }

  /**
   * Send PTT release event
   */
  sendPTTRelease() {
    this.sendMessage({
      type: 'ptt_state',
      state: 'released',
    })
  }

  /**
   * Send custom message to backend
   */
  sendMessage(message: any) {
    if (!this.client) {
      console.warn('Cannot send message: client not connected')
      return
    }

    try {
      console.log('[Pipecat] Sending message:', message)
      // Use sendClientMessage to send custom messages to the backend
      this.client.sendClientMessage(message.type || 'app-message', message)
      console.log('[Pipecat] Message sent successfully')
    } catch (error) {
      console.error('[Pipecat] Error sending message:', error)
      this.callbacks.onError?.(error as Error)
    }
  }

  /**
   * Get current connection state
   */
  isConnected(): boolean {
    return this.client?.state === 'connected'
  }

  /**
   * Enable/disable microphone
   * Note: The Pipecat SDK handles mic enable/disable through the constructor config.
   * Manual control may not be available in current SDK version.
   */
  async setMicrophoneEnabled(enabled: boolean) {
    console.warn('[Pipecat] setMicrophoneEnabled called but manual mic control not available in SDK')
    console.warn('[Pipecat] Microphone is controlled via enableMic parameter in constructor')
    // TODO: Find correct API for manual microphone control in Pipecat SDK v1.5.0
  }

  /**
   * Register event handlers for RTVI events
   */
  private registerEventHandlers() {
    if (!this.client) return

    // Connection events
    this.client.on(RTVIEvent.Connected, () => {
      console.log('RTVI Event: Connected')
      this.callbacks.onConnected?.()
    })

    this.client.on(RTVIEvent.Disconnected, () => {
      console.log('RTVI Event: Disconnected')
      this.callbacks.onDisconnected?.()
    })

    // Error events
    this.client.on(RTVIEvent.Error, (message: RTVIMessage) => {
      console.error('RTVI Event: Error', message)
      const errorData = message.data as any
      const error = new Error(errorData?.message || errorData?.error || 'Unknown error')
      this.callbacks.onError?.(error)
    })

    // Message events - listen for server messages
    this.client.on(RTVIEvent.ServerMessage, (message: RTVIMessage) => {
      this.handleMessage(message)
      this.callbacks.onMessage?.(message)
    })

    // Audio track events
    this.client.on(RTVIEvent.TrackStarted, (track: MediaStreamTrack) => {
      console.log('RTVI Event: Track started', track.kind, {
        id: track.id,
        label: track.label,
        enabled: track.enabled,
        muted: track.muted,
        readyState: track.readyState
      })
      if (track.kind === 'audio') {
        // Audio track ready for playback
        this.handleAudioTrack(track)
      }
    })

    this.client.on(RTVIEvent.TrackStopped, (track: MediaStreamTrack) => {
      console.log('RTVI Event: Track stopped', track.kind, track.id)
    })

    // Microphone events (Note: MicrophoneEnabled/Disabled events may not exist in current SDK version)
    // We'll use TrackStarted instead to detect microphone activation

    // Log all events for debugging
    this.client.on(RTVIEvent.TransportStateChanged, (state: string) => {
      console.log('[Pipecat] Transport state changed:', state)
    })
  }

  /**
   * Handle incoming messages from backend
   */
  private handleMessage(message: RTVIMessage) {
    console.log('[HANDLER] ═══ handleMessage CALLED ═══')
    console.log('[HANDLER] Raw message:', JSON.stringify(message, null, 2))

    // The onServerMessage callback receives the already-unwrapped data payload
    // So message IS the data, not a wrapper with type and data fields
    const msgData = message as any
    const type = msgData.type || (message as any).type

    console.log('[HANDLER] Message type:', type)
    console.log('[HANDLER] Message data:', msgData)

    switch (type) {
      case 'translation':
        console.log('[HANDLER] 🌐 Processing TRANSLATION')
        console.log('[HANDLER] Text:', msgData.text, 'Speaker:', msgData.speaker)
        console.log('[HANDLER] Calling onTranslation callback...')
        this.callbacks.onTranslation?.(msgData.text, msgData.speaker)
        console.log('[HANDLER] onTranslation callback completed')
        break

      case 'transcript':
        console.log('[HANDLER] 📝 Processing TRANSCRIPT')
        console.log('[HANDLER] Text:', msgData.text, 'Speaker:', msgData.speaker)
        this.callbacks.onTranscript?.(msgData.text, msgData.speaker)
        break

      case 'audio_level':
        // Uncomment for audio level debugging (can be noisy)
        // console.log('[Pipecat] 🔊 Audio level:', msgData.level, 'speaker:', msgData.speaker)
        this.callbacks.onAudioLevel?.(msgData.level, msgData.speaker)
        break

      case 'thinking':
        console.log('[Pipecat] 🤔 Thinking indicator:', msgData.is_thinking)
        this.callbacks.onThinking?.(msgData.is_thinking)
        break

      case 'connection_state':
        // Handle connection state changes
        console.log('[Pipecat] 🔌 Connection state:', msgData.state)
        break

      case 'error':
        console.error('[Pipecat] ❌ Backend error:', msgData.error_message)
        this.callbacks.onError?.(new Error(msgData.error_message))
        break

      default:
        console.log('[Pipecat] ⚠️ Unknown message type:', type, msgData)
    }
  }

  /**
   * Handle audio track for playback
   */
  private handleAudioTrack(track: MediaStreamTrack) {
    try {
      // Create media stream from track
      const stream = new MediaStream([track])

      // Create audio element for playback
      const audio = new Audio()
      audio.srcObject = stream
      audio.autoplay = true

      console.log('Audio track ready for playback')
    } catch (error) {
      console.error('Error handling audio track:', error)
      this.callbacks.onError?.(error as Error)
    }
  }

  /**
   * Get client instance (for advanced usage)
   */
  getClient(): PipecatClient | null {
    return this.client
  }
}
