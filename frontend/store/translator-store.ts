import { create } from 'zustand'
import type { TranslatorState, Message } from '@/lib/types'

export const useTranslatorStore = create<TranslatorState>((set, get) => ({
  // Connection
  connectionState: 'disconnected',
  sessionId: null,

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
    const newMessage: Message = {
      ...message,
      id: `${Date.now()}-${Math.random()}`,
      timestamp: new Date()
    }

    set((state) => ({
      messages: [...state.messages, newMessage].slice(-50) // Keep last 50 messages
    }))
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
