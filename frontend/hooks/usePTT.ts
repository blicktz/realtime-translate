import { useCallback, useRef } from 'react'
import { useTranslatorStore } from '@/store/translator-store'

export function usePTT(onPressStart?: () => void, onPressEnd?: () => void) {
  const { isPTTPressed, setPTTPressed } = useTranslatorStore()
  const touchIdRef = useRef<number | null>(null)
  const isPressingRef = useRef(false)

  const handlePressStart = useCallback((e: React.TouchEvent | React.MouseEvent) => {
    // e.preventDefault() - Removed to avoid passive listener error

    // Prevent duplicate press events
    if (isPressingRef.current) return
    isPressingRef.current = true

    // Haptic feedback
    if ('vibrate' in navigator) {
      navigator.vibrate(10)
    }

    setPTTPressed(true)

    // Track touch ID for multi-touch handling
    if ('touches' in e && e.touches.length > 0) {
      touchIdRef.current = e.touches[0].identifier
    }

    onPressStart?.()
  }, [setPTTPressed, onPressStart])

  const handlePressEnd = useCallback((e: React.TouchEvent | React.MouseEvent) => {
    // e.preventDefault() - Removed to avoid passive listener error

    if (!isPressingRef.current) return
    isPressingRef.current = false

    // Double pulse haptic feedback
    if ('vibrate' in navigator) {
      navigator.vibrate([10, 50, 10])
    }

    setPTTPressed(false)
    touchIdRef.current = null

    onPressEnd?.()
  }, [setPTTPressed, onPressEnd])

  const handleTouchCancel = useCallback((e: React.TouchEvent) => {
    // Handle interruptions (phone call, notification, etc.)
    isPressingRef.current = false
    setPTTPressed(false)
    touchIdRef.current = null
    onPressEnd?.()
  }, [setPTTPressed, onPressEnd])

  return {
    isPTTPressed,
    handlers: {
      onTouchStart: handlePressStart,
      onTouchEnd: handlePressEnd,
      onTouchCancel: handleTouchCancel,
      onMouseDown: handlePressStart,
      onMouseUp: handlePressEnd,
      onMouseLeave: handlePressEnd,
    }
  }
}
