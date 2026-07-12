import React from 'react'

export default function LoadingSpinner({ label = 'Loading…' }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-ink-500">
      <div className="w-8 h-8 rounded-full border-2 border-base-600 border-t-accent animate-spin" />
      <span className="text-xs font-mono uppercase tracking-wider">{label}</span>
    </div>
  )
}
