'use client'

import { useEffect, useRef } from 'react'
import { useTranslatorStore } from '@/store/translator-store'
import { useSettingsStore } from '@/store/settings-store'
import UserMessage from './UserMessage'
import PartnerMessage from './PartnerMessage'

export default function ChatFeed() {
  const { messages } = useTranslatorStore()
  const { homeLanguage } = useSettingsStore()
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500 text-center px-4">
        <div>
          <div className="text-4xl mb-4">🌐</div>
          <p className="text-sm">Press and hold the button to start speaking</p>
          <p className="text-xs mt-2 opacity-70">Your translations will appear here</p>
        </div>
      </div>
    )
  }

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto custom-scrollbar py-4 space-y-4"
    >
      {messages.map((message) => (
        message.speaker === 'user' ? (
          <UserMessage key={message.id} message={message} />
        ) : (
          <PartnerMessage key={message.id} message={message} />
        )
      ))}
    </div>
  )
}
