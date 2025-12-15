'use client'

import { useSettingsStore } from '@/store/settings-store'
import { useTranslatorStore } from '@/store/translator-store'

export default function SettingsPanel() {
  const {
    isOpen,
    toggleOpen,
    close,
    homeLanguage,
    targetLanguage,
    availableLanguages,
    setHomeLanguage,
    setTargetLanguage
  } = useSettingsStore()

  const { connectionState, setLanguages } = useTranslatorStore()
  const isConnected = connectionState === 'connected'

  const handleSave = () => {
    setLanguages(homeLanguage, targetLanguage)
    close()
  }

  return (
    <>
      {/* Settings Button */}
      <button
        onClick={toggleOpen}
        className="p-2 rounded-lg bg-cyber-dark border-2 border-cyber-cyan/50 hover:border-cyber-cyan transition-colors touch-manipulation"
        aria-label="Settings"
      >
        <svg className="w-6 h-6 text-cyber-cyan" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>

      {/* Settings Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-cyber-darker border-2 border-cyber-cyan rounded-lg p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-cyber-cyan cyber-text-glow">SETTINGS</h2>
              <button
                onClick={close}
                className="text-gray-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {isConnected && (
              <div className="mb-4 p-3 bg-yellow-500/10 border border-yellow-500/50 rounded text-yellow-500 text-sm">
                ⚠️ Disconnect to change languages
              </div>
            )}

            <div className="space-y-4">
              {/* Home Language */}
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  YOUR LANGUAGE (HOME)
                </label>
                <select
                  value={homeLanguage}
                  onChange={(e) => setHomeLanguage(e.target.value)}
                  disabled={isConnected}
                  className="w-full px-4 py-3 bg-cyber-dark border-2 border-cyber-cyan/50 rounded-lg text-white disabled:opacity-50 focus:border-cyber-cyan outline-none"
                >
                  {availableLanguages.map((lang) => (
                    <option key={lang.code} value={lang.code}>
                      {lang.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Target Language */}
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  PARTNER LANGUAGE (TARGET)
                </label>
                <select
                  value={targetLanguage}
                  onChange={(e) => setTargetLanguage(e.target.value)}
                  disabled={isConnected}
                  className="w-full px-4 py-3 bg-cyber-dark border-2 border-cyber-magenta/50 rounded-lg text-white disabled:opacity-50 focus:border-cyber-magenta outline-none"
                >
                  {availableLanguages.map((lang) => (
                    <option key={lang.code} value={lang.code}>
                      {lang.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <button
              onClick={handleSave}
              className="w-full mt-6 px-6 py-3 bg-cyber-cyan text-cyber-dark font-bold rounded-lg hover:bg-cyber-cyan/90 transition-colors"
            >
              SAVE
            </button>
          </div>
        </div>
      )}
    </>
  )
}
