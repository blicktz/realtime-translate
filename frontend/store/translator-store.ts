import { create } from 'zustand'
import type { TranslatorState, Message } from '@/lib/types'

export const useTranslatorStore = create<TranslatorState>((set, get) => ({
  // Connection
  connectionState: 'disconnected',
  sessionId: null,

  // Pipecat Client (shared across all components)
  pipecatClient: null,

  // PTT State
  isPTTPressed: false,
  currentSpeaker: null,

  // Processing
  isProcessing: false,
  processingStage: 'idle',

  // Messages
  messages: [],

  // Config
  homeLanguage: 'en',
  targetLanguage: 'es',

  // Audio
  audioLevel: 0,

  // Actions
  setConnectionState: (state) => set({ connectionState: state }),

  setPipecatClient: (client) => set({ pipecatClient: client }),

  setSessionId: (id) => set({ sessionId: id }),

  setPTTPressed: (pressed) => {
    set({
      isPTTPressed: pressed,
      currentSpeaker: pressed ? 'user' : null
    })
  },

  setProcessing: (processing, stage = 'idle') => {
    set({
      isProcessing: processing,
      processingStage: stage
    })
  },

  addMessage: (message) => {
    console.log('[STORE-ACTION] ═══ addMessage CALLED ═══')
    console.log('[STORE-ACTION] Input message:', message)

    const newMessage: Message = {
      ...message,
      id: `${Date.now()}-${Math.random()}`,
      timestamp: new Date()
    }

    console.log('[STORE-ACTION] New message created:', newMessage)
    console.log('[STORE-ACTION] Updating state...')

    set((state) => {
      console.log('[STORE-ACTION] Current messages count:', state.messages.length)
      const updatedMessages = [...state.messages, newMessage].slice(-50)
      console.log('[STORE-ACTION] New messages count:', updatedMessages.length)
      return { messages: updatedMessages }
    })

    console.log('[STORE-ACTION] State updated successfully')
  },

  setLanguages: (home, target) => {
    set({
      homeLanguage: home,
      targetLanguage: target
    })
  },

  setAudioLevel: (level) => set({ audioLevel: level }),

  reset: () => {
    set({
      connectionState: 'disconnected',
      sessionId: null,
      isPTTPressed: false,
      currentSpeaker: null,
      isProcessing: false,
      processingStage: 'idle',
      messages: [],
      audioLevel: 0
    })
  }
}))
