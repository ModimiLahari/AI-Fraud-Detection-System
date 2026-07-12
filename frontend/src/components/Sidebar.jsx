import React from 'react'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Users, ShieldAlert, Bell, FileBarChart, ShieldHalf } from 'lucide-react'

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/customers', label: 'Customers', icon: Users },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/reports', label: 'Reports', icon: FileBarChart },
]

export default function Sidebar() {
  return (
    <aside className="w-60 shrink-0 h-screen sticky top-0 border-r border-base-700/60 bg-base-950/60 flex flex-col">
      <div className="h-16 flex items-center gap-2.5 px-5 border-b border-base-700/60">
        <div className="w-8 h-8 rounded-lg bg-accent/15 border border-accent/30 flex items-center justify-center text-accent">
          <ShieldHalf size={18} />
        </div>
        <div>
          <div className="font-display font-semibold text-sm leading-none text-ink-100">SENTINEL</div>
          <div className="text-[10px] font-mono text-ink-500 tracking-wide mt-0.5">RISK CONTROL ROOM</div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-accent/10 text-accent border border-accent/25'
                  : 'text-ink-500 border border-transparent hover:text-ink-100 hover:bg-base-800/60'
              }`
            }
          >
            <Icon size={17} strokeWidth={2} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-3 mx-3 mb-4 rounded-lg border border-signal-high/25 bg-signal-high/5">
        <div className="flex items-center gap-2 text-signal-high text-xs font-medium">
          <ShieldAlert size={14} />
          Early Warning Active
        </div>
        <p className="text-[11px] text-ink-500 mt-1 leading-relaxed">
          Monitoring EMI bounce, fund diversion & GST mismatch signals in real time.
        </p>
      </div>
    </aside>
  )
}
