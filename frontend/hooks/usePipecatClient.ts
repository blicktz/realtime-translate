import { useEffect, useRef, useCallback } from 'react'
import { useTranslatorStore } from '@/store/translator-store'
import { NebulaTranslateClient } from '@/lib/pipecat-client'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function usePipecatClient() {
  const clientRef = useRef<NebulaTranslateClient | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined)
  const reconnectAttemptsRef = useRef(0)

  const {
    sessionId,
    setConnectionState,
    addMessage,
    setProcessing,
    setAudioLevel
  } = useTranslatorStore()

  const connect = useCallback(async (sessionId: string) => {
    try {
      setConnectionState('connecting')

      // Create new Pipecat client
      const client = new NebulaTranslateClient()
      clientRef.current = client

      // Connect with callbacks
      await client.connect(
        {
          baseUrl: API_URL,
          sessionId,
          enableMic: true,
          enableCam: false,
        },
        {
          onConnected: async () => {
            console.log('Pipecat client connected')
            setConnectionState('connected')
            reconnectAttemptsRef.current = 0

            // Explicitly enable microphone to activate transmission
            if (client) {
              const pipecatClient = client.getClient()

              if (pipecatClient && typeof pipecatClient.enableMic === 'function') {
                try {
                  console.log('[Pipecat] Calling enableMic() to activate microphone transmission...')
                  await pipecatClient.enableMic(true)
                  console.log('[Pipecat] Microphone transmission activated successfully')
                } catch (error) {
                  console.error('[Pipecat] Failed to activate microphone transmission:', error)
                }
              }

              // Debug: Log available client methods and properties
              console.log('[Pipecat] Client object methods:', Object.getOwnPropertyNames(Object.getPrototypeOf(pipecatClient || {})))

              // Check current tracks
              if (pipecatClient && typeof pipecatClient.tracks === 'function') {
                const tracks = pipecatClient.tracks()
                console.log('[Pipecat] All tracks after connection:', tracks)

                // Log detailed track info
                if (tracks?.local) {
                  const localAudio = tracks.local.audio
                  const localVideo = tracks.local.video

                  console.log('[Pipecat] Local tracks:', {
                    audio: Array.isArray(localAudio)
                      ? localAudio.map((t: MediaStreamTrack) => ({
                        id: t.id, kind: t.kind, label: t.label,
                        enabled: t.enabled, muted: t.muted, readyState: t.readyState
                      }))
                      : localAudio ? {
                        id: localAudio.id, kind: localAudio.kind, label: localAudio.label,
                        enabled: localAudio.enabled, muted: localAudio.muted, readyState: localAudio.readyState
                      } : null,
                    video: Array.isArray(localVideo)
                      ? localVideo.map((t: MediaStreamTrack) => ({
                        id: t.id, kind: t.kind, label: t.label,
                        enabled: t.enabled, muted: t.muted, readyState: t.readyState
                      }))
                      : localVideo ? {
                        id: localVideo.id, kind: localVideo.kind, label: localVideo.label,
                        enabled: localVideo.enabled, muted: localVideo.muted, readyState: localVideo.readyState
                      } : null
                  })
                }
              }

              // CRITICAL: Check WebRTC peer connection for audio senders
              try {
                if (pipecatClient) {
                  const transport = pipecatClient.transport  // Property, not a function!
                  console.log('[WebRTC] Transport object:', transport)

                  // Access the peer connection (might be _pc, pc, or peerConnection)
                  const pc = (transport as any)?._pc || (transport as any)?.pc || (transport as any)?.peerConnection

                  if (pc) {
                    console.log('[WebRTC] Peer connection found:', pc)

                    // Check senders
                    const senders = pc.getSenders()
                    console.log('[WebRTC] Peer connection senders:', senders.map((s: RTCRtpSender) => ({
                      track: s.track?.kind,
                      trackId: s.track?.id,
                      trackLabel: s.track?.label,
                      trackEnabled: s.track?.enabled,
                      trackMuted: s.track?.muted,
                      trackReadyState: s.track?.readyState
                    })))

                    // Check if audio sender exists
                    const audioSender = senders.find((s: RTCRtpSender) => s.track?.kind === 'audio')
                    if (!audioSender) {
                      console.error('[WebRTC] ❌ NO AUDIO SENDER! Mic track NOT added to peer connection!')
                    } else {
                      console.log('[WebRTC] ✅ Audio sender found:', audioSender.track)
                    }

                    // Check SDP
                    const localDesc = pc.localDescription
                    if (localDesc) {
                      console.log('[WebRTC] Local SDP type:', localDesc.type)
                      const hasAudio = localDesc.sdp.includes('m=audio')
                      console.log('[WebRTC] SDP includes audio:', hasAudio)
                      if (!hasAudio) {
                        console.error('[WebRTC] ❌ SDP does NOT include audio media line!')
                      }
                    }
                  } else {
                    console.error('[WebRTC] ❌ Could not access peer connection object')
                  }
                }
              } catch (error) {
                console.error('[WebRTC] Error inspecting peer connection:', error)
              }
            }
          },

          onDisconnected: () => {
            console.log('Pipecat client disconnected')
            setConnectionState('disconnected')

            // Attempt to reconnect with exponential backoff
            if (reconnectAttemptsRef.current < 5) {
              const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000)
              reconnectTimeoutRef.current = setTimeout(() => {
                reconnectAttemptsRef.current++
                connect(sessionId)
              }, delay)
            }
          },

          onError: (error) => {
            console.error('Pipecat client error:', error)
            setConnectionState('disconnected')
          },

          onTranslation: (text, speaker) => {
            addMessage({
              speaker,
              text,
              isTranslation: true
            })
          },

          onThinking: (isThinking) => {
            setProcessing(isThinking)
          },

          onAudioLevel: (level, speaker) => {
            setAudioLevel(level)
          },
        }
      )

    } catch (err) {
      console.error('Failed to connect Pipecat client:', err)
      setConnectionState('disconnected')
    }
  }, [setConnectionState, addMessage, setProcessing, setAudioLevel])

  const disconnect = useCallback(async () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }

    if (clientRef.current) {
      await clientRef.current.disconnect()
      clientRef.current = null
    }

    setConnectionState('disconnected')
  }, [setConnectionState])

  const sendPTTPress = useCallback(() => {
    console.log('[usePipecatClient] sendPTTPress called')
    if (clientRef.current?.isConnected()) {
      clientRef.current.sendPTTPress()
    } else {
      console.warn('[usePipecatClient] sendPTTPress called but client not connected')
    }
  }, [])

  const sendPTTRelease = useCallback(() => {
    if (clientRef.current?.isConnected()) {
      clientRef.current.sendPTTRelease()
    }
  }, [])

  const sendMessage = useCallback((message: any) => {
    if (clientRef.current?.isConnected()) {
      clientRef.current.sendMessage(message)
    }
  }, [])

  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return {
    connect,
    disconnect,
    sendMessage,
    sendPTTPress,
    sendPTTRelease,
    isConnected: clientRef.current?.isConnected() ?? false,
    client: clientRef.current
  }
}
