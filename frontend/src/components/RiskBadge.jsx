import React from 'react'

const STYLES = {
  Low: 'text-signal-low bg-signal-low/10 border-signal-low/30',
  Medium: 'text-signal-medium bg-signal-medium/10 border-signal-medium/30',
  High: 'text-signal-high bg-signal-high/10 border-signal-high/30',
  Critical: 'text-signal-critical bg-signal-critical/10 border-signal-critical/30',
  'Not Evaluated': 'text-ink-500 bg-base-700/50 border-base-600',
}

export default function RiskBadge({ level, className = '' }) {
  const style = STYLES[level] || STYLES['Not Evaluated']
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-mono font-medium ${style} ${className}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {level}
    </span>
  )
}
