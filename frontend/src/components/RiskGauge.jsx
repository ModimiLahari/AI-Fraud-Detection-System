import React from 'react'

const LEVELS = [
  { max: 20, color: '#34D399', label: 'Low' },
  { max: 45, color: '#F2C94C', label: 'Medium' },
  { max: 70, color: '#F5A623', label: 'High' },
  { max: 100, color: '#E5484D', label: 'Critical' },
]

function colorForScore(score) {
  return LEVELS.find((l) => score <= l.max)?.color || '#E5484D'
}

// Semicircular instrument-style gauge, 180deg sweep, tick marks every 10 points.
export default function RiskGauge({ score = 0, size = 220 }) {
  const clamped = Math.max(0, Math.min(100, score))
  const angle = (clamped / 100) * 180 // 0 -> left, 180 -> right
  const radius = size / 2 - 18
  const cx = size / 2
  const cy = size / 2

  const needleRad = ((180 - angle) * Math.PI) / 180
  const needleX = cx + radius * 0.82 * Math.cos(needleRad)
  const needleY = cy - radius * 0.82 * Math.sin(needleRad)

  const ticks = Array.from({ length: 11 }, (_, i) => i * 10)
  const color = colorForScore(clamped)

  return (
    <div className="flex flex-col items-center select-none">
      <svg width={size} height={size / 2 + 30} viewBox={`0 0 ${size} ${size / 2 + 30}`}>
        {/* Base arc segments by risk band */}
        {LEVELS.map((lvl, i) => {
          const prevMax = i === 0 ? 0 : LEVELS[i - 1].max
          const a0 = (prevMax / 100) * 180
          const a1 = (lvl.max / 100) * 180
          const r0 = ((180 - a0) * Math.PI) / 180
          const r1 = ((180 - a1) * Math.PI) / 180
          const x0 = cx + radius * Math.cos(r0)
          const y0 = cy - radius * Math.sin(r0)
          const x1 = cx + radius * Math.cos(r1)
          const y1 = cy - radius * Math.sin(r1)
          return (
            <path
              key={lvl.label}
              d={`M ${x0} ${y0} A ${radius} ${radius} 0 0 1 ${x1} ${y1}`}
              stroke={lvl.color}
              strokeWidth={10}
              strokeOpacity={0.85}
              fill="none"
              strokeLinecap="butt"
            />
          )
        })}

        {/* Tick marks */}
        {ticks.map((t) => {
          const a = (t / 100) * 180
          const rad = ((180 - a) * Math.PI) / 180
          const inner = radius - 14
          const outer = radius - 4
          const x1 = cx + inner * Math.cos(rad)
          const y1 = cy - inner * Math.sin(rad)
          const x2 = cx + outer * Math.cos(rad)
          const y2 = cy - outer * Math.sin(rad)
          return (
            <line key={t} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#5B6780" strokeWidth={1.5} />
          )
        })}

        {/* Needle */}
        <line
          x1={cx}
          y1={cy}
          x2={needleX}
          y2={needleY}
          stroke={color}
          strokeWidth={3}
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 6px ${color})` }}
        />
        <circle cx={cx} cy={cy} r={6} fill={color} />
        <circle cx={cx} cy={cy} r={9} fill="none" stroke={color} strokeOpacity={0.4} strokeWidth={2} />
      </svg>

      <div className="-mt-2 text-center">
        <div className="font-mono text-3xl font-semibold" style={{ color }}>
          {clamped}
          <span className="text-ink-500 text-base">/100</span>
        </div>
        <div className="eyebrow mt-0.5" style={{ color }}>
          {LEVELS.find((l) => clamped <= l.max)?.label} Risk
        </div>
      </div>
    </div>
  )
}
