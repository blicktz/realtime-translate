'use client'

import { useEffect, useRef } from 'react'
import MainLayout from '@/components/layout/MainLayout'
import ConnectionToggle from '@/components/ui/ConnectionToggle'
import PTTButton from '@/components/ui/PTTButton'
import AudioVisualizer from '@/components/ui/AudioVisualizer'
import ThinkingIndicator from '@/components/ui/ThinkingIndicator'
import ChatFeed from '@/components/chat/ChatFeed'
import SettingsPanel from '@/components/ui/SettingsPanel'
import { useTranslatorStore } from '@/store/translator-store'
import { useWakeLock } from '@/hooks/useWakeLock'
import { usePipecatClient } from '@/hooks/usePipecatClient'

export default function Home() {
  const { connectionState, isProcessing, setPipecatClient } = useTranslatorStore()
  const isConnected = connectionState === 'connected'

  // Initialize Pipecat client ONCE and store in Zustand for all components to access
  const pipecatClient = usePipecatClient()
  const hasStoredClient = useRef(false)

  // Store Pipecat client in Zustand so all components can access it (run only once)
  useEffect(() => {
    if (!hasStoredClient.current) {
      console.log('[App] Storing Pipecat client in Zustand store')
      setPipecatClient(pipecatClient as any)
      hasStoredClient.current = true
    }
  }, []) // Empty dependencies - run only once on mount

  // Request wake lock when connected
  useWakeLock(isConnected)

  // Handle viewport height on mobile
  useEffect(() => {
    const setVH = () => {
      const vh = window.innerHeight * 0.01
      document.documentElement.style.setProperty('--vh', `${vh}px`)
    }

    setVH()
    window.addEventListener('resize', setVH)
    window.addEventListener('orientationchange', setVH)

    return () => {
      window.removeEventListener('resize', setVH)
      window.removeEventListener('orientationchange', setVH)
    }
  }, [])

  return (
    <MainLayout>
      {/* Header: Connection and Settings */}
      <div className="flex justify-between items-center p-4 safe-area-padding">
        <ConnectionToggle />
        <SettingsPanel />
      </div>

      {/* Chat Feed */}
      <div className="flex-1 overflow-hidden px-4">
        <ChatFeed />
      </div>

      {/* Audio Visualizer */}
      <div className="relative h-20 mx-4">
        <AudioVisualizer />
        {isProcessing && <ThinkingIndicator />}
      </div>

      {/* PTT Button */}
      <div className="pb-safe-bottom">
        <PTTButton disabled={!isConnected} />
      </div>
    </MainLayout>
  )
}
