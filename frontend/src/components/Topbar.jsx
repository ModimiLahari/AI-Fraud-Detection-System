import React from 'react'
import { LogOut, Bell } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { Link } from 'react-router-dom'

export default function Topbar({ title, subtitle, unreadAlerts = 0 }) {
  const { user, signOut } = useAuth()

  return (
    <header className="h-16 sticky top-0 z-10 flex items-center justify-between px-6 border-b border-base-700/60 bg-base-900/80 backdrop-blur-md">
      <div>
        <h1 className="text-lg font-semibold text-ink-100 leading-none">{title}</h1>
        {subtitle && <p className="text-xs text-ink-500 mt-1">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-4">
        <Link to="/alerts" className="relative p-2 rounded-lg hover:bg-base-800 transition-colors text-ink-300">
          <Bell size={18} />
          {unreadAlerts > 0 && (
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-signal-critical" />
          )}
        </Link>

        <div className="h-8 w-px bg-base-700" />

        <div className="text-right">
          <div className="text-sm font-medium text-ink-100 leading-none">{user?.full_name}</div>
          <div className="text-[11px] text-ink-500 mt-1 capitalize">{user?.role?.replace('_', ' ')}</div>
        </div>
        <button
          onClick={signOut}
          className="p-2 rounded-lg hover:bg-base-800 text-ink-500 hover:text-signal-critical transition-colors"
          title="Log out"
        >
          <LogOut size={17} />
        </button>
      </div>
    </header>
  )
}
