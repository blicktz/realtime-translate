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
      this.transport = new SmallWebRTCTransport({
        baseUrl: config.baseUrl,
        sessionId: config.sessionId,
      })

      // Create Pipecat client with transport
      // NOTE: enableMic/enableCam must be set at CLIENT level, not transport level
      this.client = new PipecatClient({
        transport: this.transport,
        enableMic: config.enableMic ?? true,
        enableCam: config.enableCam ?? false,
        params: {
          sessionId: config.sessionId,
        },
      })
      console.log('[Pipecat] Initialized client with config:', {
        enableMic: config.enableMic ?? true,
        enableCam: config.enableCam ?? false,
        sessionId: config.sessionId
      })

      // Register event handlers
      this.registerEventHandlers()

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
      this.client.sendMessage(message)
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
    this.client.on(RTVIEvent.Error, (error: Error) => {
      console.error('RTVI Event: Error', error)
      this.callbacks.onError?.(error)
    })

    // Message events
    this.client.on(RTVIEvent.MessageReceived, (message: RTVIMessage) => {
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

    // Microphone events
    this.client.on(RTVIEvent.MicrophoneEnabled, () => {
      console.log('[Pipecat] RTVI Event: Microphone enabled ✓')
      // Log mic tracks for debugging
      if (this.client) {
        const tracks = this.client.tracks()
        console.log('[Pipecat] Current tracks:', {
          local: tracks?.local,
          remote: tracks?.remote
        })
        if (tracks?.local?.audio) {
          console.log('[Pipecat] Local audio track details:', {
            id: tracks.local.audio.id,
            enabled: tracks.local.audio.enabled,
            muted: tracks.local.audio.muted,
            readyState: tracks.local.audio.readyState,
            label: tracks.local.audio.label
          })
        } else {
          console.warn('[Pipecat] No local audio track found despite MicrophoneEnabled event!')
        }
      }
    })

    this.client.on(RTVIEvent.MicrophoneDisabled, () => {
      console.log('[Pipecat] RTVI Event: Microphone disabled')
    })

    // Log all events for debugging
    this.client.on(RTVIEvent.TransportStateChanged, (state: string) => {
      console.log('[Pipecat] Transport state changed:', state)
    })
  }

  /**
   * Handle incoming messages from backend
   */
  private handleMessage(message: RTVIMessage) {
    const { type, ...data } = message

    switch (type) {
      case 'transcript':
        this.callbacks.onTranscript?.(data.text, data.speaker)
        break

      case 'translation':
        this.callbacks.onTranslation?.(data.text, data.speaker)
        break

      case 'audio_level':
        this.callbacks.onAudioLevel?.(data.level, data.speaker)
        break

      case 'thinking':
        this.callbacks.onThinking?.(data.is_thinking)
        break

      case 'connection_state':
        // Handle connection state changes
        console.log('Connection state:', data.state)
        break

      case 'error':
        console.error('Backend error:', data.error_message)
        this.callbacks.onError?.(new Error(data.error_message))
        break

      default:
        console.log('Unknown message type:', type, data)
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
