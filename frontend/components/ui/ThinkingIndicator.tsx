'use client'

export default function ThinkingIndicator() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-cyber-dark/80 backdrop-blur-sm rounded-lg">
      <div className="flex items-center space-x-2 px-6 py-3 rounded-full bg-cyber-cyan/20 border-2 border-cyber-cyan">
        <div className="flex space-x-1">
          <div className="w-2 h-2 bg-cyber-cyan rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-2 h-2 bg-cyber-cyan rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-2 h-2 bg-cyber-cyan rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
        <span className="text-cyber-cyan font-bold text-sm ml-2">
          NEBULA IS THINKING
        </span>
      </div>
    </div>
  )
}
