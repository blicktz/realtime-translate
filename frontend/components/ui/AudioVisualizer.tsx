'use client'

import { useEffect, useRef } from 'react'
import { useTranslatorStore } from '@/store/translator-store'

const BAR_COUNT = 50
const BAR_WIDTH = 4
const BAR_GAP = 2

export default function AudioVisualizer() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationFrameRef = useRef<number | undefined>(undefined)
  const { audioLevel, currentSpeaker, isPTTPressed } = useTranslatorStore()

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const draw = () => {
      const width = canvas.width
      const height = canvas.height

      // Clear canvas
      ctx.fillStyle = '#0a0a0f'
      ctx.fillRect(0, 0, width, height)

      // Determine color based on speaker
      const color = isPTTPressed ? '#00ffff' : '#ff00ff'

      // Draw bars
      const totalWidth = BAR_COUNT * (BAR_WIDTH + BAR_GAP)
      const startX = (width - totalWidth) / 2

      for (let i = 0; i < BAR_COUNT; i++) {
        const x = startX + i * (BAR_WIDTH + BAR_GAP)

        // Simulate waveform with randomness and audio level
        const randomHeight = Math.random() * 0.5 + 0.5
        const barHeight = Math.max(2, (height * audioLevel * randomHeight) / 2)

        const y = (height - barHeight) / 2

        // Gradient effect
        const gradient = ctx.createLinearGradient(0, y, 0, y + barHeight)
        gradient.addColorStop(0, color)
        gradient.addColorStop(1, color + '80')

        ctx.fillStyle = gradient
        ctx.fillRect(x, y, BAR_WIDTH, barHeight)
      }

      animationFrameRef.current = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
    }
  }, [audioLevel, currentSpeaker, isPTTPressed])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const resize = () => {
      canvas.width = canvas.offsetWidth
      canvas.height = canvas.offsetHeight
    }

    resize()
    window.addEventListener('resize', resize)

    return () => window.removeEventListener('resize', resize)
  }, [])

  return (
    <div className="w-full h-full relative">
      <canvas
        ref={canvasRef}
        className="w-full h-full rounded-lg bg-cyber-darker"
      />
    </div>
  )
}
