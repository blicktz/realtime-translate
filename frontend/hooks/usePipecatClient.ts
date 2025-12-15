import { useEffect, useRef, useCallback } from 'react'
import { useTranslatorStore } from '@/store/translator-store'
import { NebulaTranslateClient } from '@/lib/pipecat-client'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function usePipecatClient() {
  const clientRef = useRef<NebulaTranslateClient | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
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
          onConnected: () => {
            console.log('Pipecat client connected')
            setConnectionState('connected')
            reconnectAttemptsRef.current = 0
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
    if (clientRef.current?.isConnected()) {
      clientRef.current.sendPTTPress()
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
