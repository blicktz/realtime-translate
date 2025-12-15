'use client'

import { usePipecatClient } from '@/hooks/usePipecatClient'
import { usePTT } from '@/hooks/usePTT'

interface PTTButtonProps {
  disabled?: boolean
}

export default function PTTButton({ disabled = false }: PTTButtonProps) {
  const { sendPTTPress, sendPTTRelease } = usePipecatClient()

  const { isPTTPressed, handlers } = usePTT(
    () => {
      // On press start
      sendPTTPress()
    },
    () => {
      // On press end
      sendPTTRelease()
    }
  )

  return (
    <div className="flex justify-center items-center py-8 px-4">
      <button
        {...handlers}
        disabled={disabled}
        className={`
          relative w-64 h-64 rounded-full
          flex items-center justify-center
          font-bold text-lg tracking-wider
          transition-all duration-200
          touch-none
          ${disabled
            ? 'bg-gray-800 border-gray-600 text-gray-500 cursor-not-allowed'
            : isPTTPressed
              ? 'bg-cyber-cyan/30 border-cyber-cyan text-cyber-cyan cyber-glow scale-95'
              : 'bg-cyber-dark border-cyber-cyan/50 text-cyber-cyan/70 hover:border-cyber-cyan'
          }
          border-4
        `}
      >
        <div className="text-center">
          <div className="text-2xl mb-2">
            {isPTTPressed ? '🎤' : '👆'}
          </div>
          <div>
            {isPTTPressed ? 'SPEAKING...' : 'HOLD TO SPEAK'}
          </div>
        </div>

        {/* Animated ring when pressed */}
        {isPTTPressed && (
          <div className="absolute inset-0 rounded-full border-4 border-cyber-cyan animate-ping opacity-75" />
        )}
      </button>
    </div>
  )
}
