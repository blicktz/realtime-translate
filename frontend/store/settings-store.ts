import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { SettingsState } from '@/lib/types'

const DEFAULT_LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'es', name: 'Español' },
  { code: 'fr', name: 'Français' },
  { code: 'de', name: 'Deutsch' },
  { code: 'it', name: 'Italiano' },
  { code: 'pt', name: 'Português' },
  { code: 'ja', name: '日本語' },
  { code: 'ko', name: '한국어' },
  { code: 'zh', name: '中文' },
]

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      homeLanguage: 'en',
      targetLanguage: 'es',
      availableLanguages: DEFAULT_LANGUAGES,
      isOpen: false,

      setHomeLanguage: (lang) => set({ homeLanguage: lang }),

      setTargetLanguage: (lang) => set({ targetLanguage: lang }),

      setAvailableLanguages: (languages) => set({ availableLanguages: languages }),

      toggleOpen: () => set((state) => ({ isOpen: !state.isOpen })),

      close: () => set({ isOpen: false })
    }),
    {
      name: 'nebula-settings', // localStorage key
      partialize: (state) => ({
        homeLanguage: state.homeLanguage,
        targetLanguage: state.targetLanguage
      })
    }
  )
)
