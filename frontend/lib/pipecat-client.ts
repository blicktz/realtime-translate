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
        enableMic: config.enableMic ?? true,
        enableCam: config.enableCam ?? false,
      })

      // Create Pipecat client with transport
      this.client = new PipecatClient({
        transport: this.transport,
        params: {
          sessionId: config.sessionId,
        },
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
      this.client.sendMessage(message)
    } catch (error) {
      console.error('Error sending message:', error)
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
   */
  async setMicrophoneEnabled(enabled: boolean) {
    if (!this.client) return

    try {
      if (enabled) {
        await this.client.enableMic()
      } else {
        await this.client.disableMic()
      }
    } catch (error) {
      console.error('Error toggling microphone:', error)
      this.callbacks.onError?.(error as Error)
    }
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
      console.log('RTVI Event: Track started', track.kind)
      if (track.kind === 'audio') {
        // Audio track ready for playback
        this.handleAudioTrack(track)
      }
    })

    // Microphone events
    this.client.on(RTVIEvent.MicrophoneEnabled, () => {
      console.log('RTVI Event: Microphone enabled')
    })

    this.client.on(RTVIEvent.MicrophoneDisabled, () => {
      console.log('RTVI Event: Microphone disabled')
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
