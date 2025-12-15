import { useEffect, useRef } from 'react'

export function useWakeLock(isActive: boolean) {
  const wakeLockRef = useRef<WakeLockSentinel | null>(null)

  useEffect(() => {
    const requestWakeLock = async () => {
      try {
        if ('wakeLock' in navigator && isActive) {
          wakeLockRef.current = await navigator.wakeLock.request('screen')
          console.log('Wake Lock acquired')
        }
      } catch (err) {
        console.warn('Wake Lock failed:', err)
      }
    }

    const releaseWakeLock = async () => {
      if (wakeLockRef.current) {
        try {
          await wakeLockRef.current.release()
          wakeLockRef.current = null
          console.log('Wake Lock released')
        } catch (err) {
          console.warn('Wake Lock release failed:', err)
        }
      }
    }

    if (isActive) {
      requestWakeLock()
    } else {
      releaseWakeLock()
    }

    // Re-acquire wake lock if visibility changes
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && isActive) {
        requestWakeLock()
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      releaseWakeLock()
    }
  }, [isActive])
}
