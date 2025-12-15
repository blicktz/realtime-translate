import { useEffect, useRef, useCallback } from 'react'
import { useTranslatorStore } from '@/store/translator-store'
import type { WebSocketMessage } from '@/lib/types'

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
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

      const ws = new WebSocket(`${WS_URL}/ws/session/${sessionId}`)

      ws.onopen = () => {
        console.log('WebSocket connected')
        setConnectionState('connected')
        reconnectAttemptsRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data)
          handleMessage(data)
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setConnectionState('disconnected')

        // Attempt to reconnect with exponential backoff
        if (reconnectAttemptsRef.current < 5) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000)
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++
            connect(sessionId)
          }, delay)
        }
      }

      wsRef.current = ws
    } catch (err) {
      console.error('Failed to connect WebSocket:', err)
      setConnectionState('disconnected')
    }
  }, [setConnectionState, sessionId])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setConnectionState('disconnected')
  }, [setConnectionState])

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }, [])

  const handleMessage = (data: WebSocketMessage) => {
    switch (data.type) {
      case 'connection_state':
        setConnectionState(data.state)
        break

      case 'translation':
        addMessage({
          speaker: data.speaker,
          text: data.text,
          isTranslation: true
        })
        break

      case 'thinking':
        setProcessing(data.is_thinking)
        break

      case 'audio_level':
        setAudioLevel(data.level)
        break

      case 'audio_output':
        // Handle TTS audio output
        playAudio(data.audio)
        break

      case 'error':
        console.error('Backend error:', data.error_message)
        break
    }
  }

  const playAudio = async (base64Audio: string) => {
    try {
      // Decode base64 audio
      const audioData = atob(base64Audio)
      const arrayBuffer = new ArrayBuffer(audioData.length)
      const view = new Uint8Array(arrayBuffer)

      for (let i = 0; i < audioData.length; i++) {
        view[i] = audioData.charCodeAt(i)
      }

      // Play audio
      const audioContext = new AudioContext()
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)
      const source = audioContext.createBufferSource()
      source.buffer = audioBuffer
      source.connect(audioContext.destination)
      source.start(0)
    } catch (err) {
      console.error('Failed to play audio:', err)
    }
  }

  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return {
    connect,
    disconnect,
    sendMessage,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN
  }
}
