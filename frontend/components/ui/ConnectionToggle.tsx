'use client'

import { useCallback } from 'react'
import { useTranslatorStore } from '@/store/translator-store'
import { useSettingsStore } from '@/store/settings-store'
import { usePipecatClient } from '@/hooks/usePipecatClient'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function ConnectionToggle() {
  const { connectionState, setSessionId, reset } = useTranslatorStore()
  const { homeLanguage, targetLanguage } = useSettingsStore()
  const { connect, disconnect } = usePipecatClient()

  const handleConnect = useCallback(async () => {
    try {
      // Create session
      const response = await fetch(`${API_URL}/api/session/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          home_language: homeLanguage,
          target_language: targetLanguage
        })
      })

      if (!response.ok) throw new Error('Failed to create session')

      const data = await response.json()
      setSessionId(data.session_id)

      // Connect Pipecat client
      await connect(data.session_id)
    } catch (err) {
      console.error('Connection failed:', err)
      reset()
    }
  }, [homeLanguage, targetLanguage, setSessionId, connect, reset])

  const handleDisconnect = useCallback(async () => {
    await disconnect()
    reset()
  }, [disconnect, reset])

  const handleToggle = () => {
    if (connectionState === 'disconnected') {
      handleConnect()
    } else {
      handleDisconnect()
    }
  }

  const getButtonStyle = () => {
    switch (connectionState) {
      case 'connected':
        return 'bg-cyber-cyan/20 border-cyber-cyan text-cyber-cyan cyber-glow'
      case 'connecting':
        return 'bg-cyber-blue/20 border-cyber-blue text-cyber-blue animate-pulse'
      default:
        return 'bg-gray-800 border-gray-600 text-gray-400'
    }
  }

  const getButtonText = () => {
    switch (connectionState) {
      case 'connected':
        return 'CONNECTED'
      case 'connecting':
        return 'CONNECTING...'
      default:
        return 'CONNECT'
    }
  }

  return (
    <button
      onClick={handleToggle}
      disabled={connectionState === 'connecting'}
      className={`
        px-6 py-2 rounded-lg border-2 font-bold text-sm
        transition-all duration-300 touch-manipulation
        ${getButtonStyle()}
        disabled:opacity-50
      `}
    >
      {getButtonText()}
    </button>
  )
}
