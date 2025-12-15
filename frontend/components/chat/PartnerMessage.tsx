import type { Message } from '@/lib/types'

interface PartnerMessageProps {
  message: Message
}

export default function PartnerMessage({ message }: PartnerMessageProps) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[80%]">
        <div className="text-xs text-cyber-magenta/70 mb-1">
          PARTNER (TRANSLATION)
        </div>
        <div className="bg-cyber-magenta/10 border-2 border-cyber-magenta/50 rounded-lg px-4 py-3">
          <p className="text-white text-sm">{message.text}</p>
          <div className="text-xs text-cyber-magenta/50 mt-1">
            {message.timestamp.toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit'
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
