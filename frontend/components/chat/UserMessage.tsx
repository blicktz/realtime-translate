import type { Message } from '@/lib/types'

interface UserMessageProps {
  message: Message
}

export default function UserMessage({ message }: UserMessageProps) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%]">
        <div className="text-xs text-cyber-cyan/70 mb-1 text-right">
          YOU
        </div>
        <div className="bg-cyber-cyan/10 border-2 border-cyber-cyan rounded-lg px-4 py-3 cyber-glow">
          <p className="text-white text-sm">{message.text}</p>
          <div className="text-xs text-cyber-cyan/50 mt-1 text-right">
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
