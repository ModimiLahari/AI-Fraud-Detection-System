import React, { useEffect, useState } from 'react'
import { CheckCheck, Bell } from 'lucide-react'
import toast from 'react-hot-toast'
import { Link } from 'react-router-dom'
import Topbar from '../components/Topbar'
import RiskBadge from '../components/RiskBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import { getAlerts, markAlertRead } from '../api/fraud'

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('All')

  function load() {
    setLoading(true)
    getAlerts().then(setAlerts).finally(() => setLoading(false))
  }

  useEffect(load, [])

  async function handleMarkRead(id) {
    try {
      await markAlertRead(id)
      setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, is_read: true } : a)))
    } catch {
      toast.error('Failed to update alert')
    }
  }

  const filtered = filter === 'All' ? alerts : alerts.filter((a) => a.severity === filter)

  return (
    <>
      <Topbar title="Alerts" subtitle="Real-time notifications from the fraud detection engine" />
      <div className="p-6 space-y-5">
        <div className="flex gap-2">
          {['All', 'Critical', 'High', 'Medium', 'Low'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`text-xs font-mono px-3 py-1.5 rounded-full border transition-colors ${
                filter === f
                  ? 'bg-accent/15 border-accent/40 text-accent'
                  : 'border-base-600 text-ink-500 hover:text-ink-100'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        {loading ? (
          <LoadingSpinner />
        ) : filtered.length === 0 ? (
          <div className="panel py-16 flex flex-col items-center text-ink-500">
            <Bell size={28} className="mb-3 opacity-40" />
            <p className="text-sm">No alerts to show.</p>
          </div>
        ) : (
          <div className="panel divide-y divide-base-700/50">
            {filtered.map((a) => (
              <div key={a.id} className={`flex items-start justify-between p-4 ${!a.is_read ? 'bg-accent/[0.03]' : ''}`}>
                <div className="flex items-start gap-3 min-w-0">
                  <RiskBadge level={a.severity} />
                  <div className="min-w-0">
                    <Link to={`/customers/${a.customer_id}`} className="text-sm font-medium text-ink-100 hover:text-accent">
                      {a.title}
                    </Link>
                    <p className="text-xs text-ink-500 mt-1">{a.message}</p>
                    <p className="text-[11px] font-mono text-ink-700 mt-1.5">
                      {new Date(a.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                {!a.is_read && (
                  <button
                    onClick={() => handleMarkRead(a.id)}
                    className="text-ink-500 hover:text-accent p-1.5 rounded-lg hover:bg-base-700/50 shrink-0"
                    title="Mark as read"
                  >
                    <CheckCheck size={16} />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
