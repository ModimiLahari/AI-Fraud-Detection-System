import React from 'react'

export default function StatCard({ icon: Icon, label, value, hint, accentClass = 'text-accent' }) {
  return (
    <div className="panel p-5 flex items-start justify-between">
      <div>
        <div className="eyebrow">{label}</div>
        <div className="font-display text-3xl font-semibold mt-2 text-ink-100">{value}</div>
        {hint && <div className="text-xs text-ink-500 mt-1.5">{hint}</div>}
      </div>
      {Icon && (
        <div className={`w-10 h-10 rounded-xl bg-base-700/60 flex items-center justify-center ${accentClass}`}>
          <Icon size={18} strokeWidth={2} />
        </div>
      )}
    </div>
  )
}
