/**
 * Type definitions for Nebula Translate frontend
 */

export type ConnectionState = 'disconnected' | 'connecting' | 'connected'

export type SpeakerTurn = 'user' | 'partner'

export type ProcessingStage = 'idle' | 'stt' | 'translation' | 'tts' | 'complete'

export type LanguageCode = string

export interface Message {
  id: string
  speaker: SpeakerTurn
  text: string
  timestamp: Date
  isTranslation: boolean
}

export interface SessionConfig {
  sessionId: string
  homeLanguage: LanguageCode
  targetLanguage: LanguageCode
}

export interface WebSocketMessage {
  type: string
  [key: string]: any
}

export interface Language {
  code: string
  name: string
}

export interface AudioLevel {
  level: number
  speaker: SpeakerTurn
}

// Pipecat Client interface
export interface PipecatClient {
  connect: (sessionId: string) => Promise<void>
  disconnect: () => Promise<void>
  sendPTTPress: () => void
  sendPTTRelease: () => void
  sendMessage: (message: any) => void
  isConnected: boolean
  client: any
}

// Store state interface
export interface TranslatorState {
  // Connection
  connectionState: ConnectionState
  sessionId: string | null

  // Pipecat Client (shared across all components)
  pipecatClient: PipecatClient | null

  // PTT State
  isPTTPressed: boolean
  currentSpeaker: SpeakerTurn | null

  // Processing
  isProcessing: boolean
  processingStage: ProcessingStage

  // Messages
  messages: Message[]

  // Config
  homeLanguage: LanguageCode
  targetLanguage: LanguageCode

  // Audio
  audioLevel: number

  // Actions
  setConnectionState: (state: ConnectionState) => void
  setSessionId: (id: string | null) => void
  setPipecatClient: (client: PipecatClient | null) => void
  setPTTPressed: (pressed: boolean) => void
  setProcessing: (processing: boolean, stage?: ProcessingStage) => void
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void
  setLanguages: (home: LanguageCode, target: LanguageCode) => void
  setAudioLevel: (level: number) => void
  reset: () => void
}

// Settings state interface
export interface SettingsState {
  homeLanguage: LanguageCode
  targetLanguage: LanguageCode
  availableLanguages: Language[]
  isOpen: boolean

  setHomeLanguage: (lang: LanguageCode) => void
  setTargetLanguage: (lang: LanguageCode) => void
  setAvailableLanguages: (languages: Language[]) => void
  toggleOpen: () => void
  close: () => void
}

// WebRTC/Audio types
export interface AudioProcessorMessage {
  type: 'audio-level'
  level: number
}

export interface WebRTCConfig {
  iceServers: RTCIceServer[]
}
