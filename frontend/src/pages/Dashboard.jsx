import React, { useEffect, useRef, useState } from 'react'
import { Users, ShieldAlert, Bell, TrendingUp, Radio } from 'lucide-react'
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import Topbar from '../components/Topbar'
import StatCard from '../components/StatCard'
import LoadingSpinner from '../components/LoadingSpinner'
import RiskBadge from '../components/RiskBadge'
import { getDashboardSummary, getAlerts } from '../api/fraud'
import { Link } from 'react-router-dom'

const REFRESH_INTERVAL_MS = 7000

const RISK_COLORS = {
  Low: '#34D399',
  Medium: '#F2C94C',
  High: '#F5A623',
  Critical: '#E5484D',
  'Not Evaluated': '#5B6780',
}

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)
  const isFirstLoad = useRef(true)

  function refresh() {
    Promise.all([getDashboardSummary(), getAlerts()])
      .then(([s, a]) => {
        setSummary(s)
        setAlerts(a)
        setLastUpdated(new Date())
      })
      .finally(() => {
        if (isFirstLoad.current) {
          setLoading(false)
          isFirstLoad.current = false
        }
      })
  }

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, REFRESH_INTERVAL_MS)
    return () => clearInterval(id)
  }, [])

  if (loading) return <LoadingSpinner label="Loading dashboard…" />
  if (!summary) return null

  const pieData = Object.entries(summary.risk_distribution)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }))

  const branchData = Object.entries(summary.branch_wise_risk).map(([branch, counts]) => ({
    branch: branch.replace(' Branch', ''),
    Low: counts.Low,
    Medium: counts.Medium,
    High: counts.High,
    Critical: counts.Critical,
  }))

  const highRiskCount = summary.risk_distribution.High + summary.risk_distribution.Critical

  return (
    <>
      <Topbar
        title="Risk Control Room"
        subtitle="Live overview of portfolio-wide fraud & early-warning signals"
        unreadAlerts={summary.unread_alerts}
      />
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-end -mt-2 -mb-2 gap-1.5 text-[11px] font-mono text-ink-500">
          <Radio size={11} className="text-signal-low animate-pulse" />
          Live · updates every {REFRESH_INTERVAL_MS / 1000}s
          {lastUpdated && <span className="text-ink-700">· last refreshed {lastUpdated.toLocaleTimeString()}</span>}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Users} label="Total Customers" value={summary.total_customers} accentClass="text-accent" />
          <StatCard
            icon={ShieldAlert}
            label="High + Critical Risk"
            value={highRiskCount}
            hint="Needs officer attention"
            accentClass="text-signal-critical"
          />
          <StatCard icon={Bell} label="Unread Alerts" value={summary.unread_alerts} accentClass="text-signal-high" />
          <StatCard icon={TrendingUp} label="Total Alerts Logged" value={summary.total_alerts} accentClass="text-signal-info" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
          <div className="panel p-5 lg:col-span-2">
            <div className="eyebrow mb-1">Fraud Distribution</div>
            <h3 className="font-display text-sm font-semibold text-ink-100 mb-4">Portfolio Risk Split</h3>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={3}
                >
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={RISK_COLORS[entry.name]} stroke="none" />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#121A2B', border: '1px solid #293552', borderRadius: 8, fontSize: 12 }}
                />
                <Legend
                  iconType="circle"
                  wrapperStyle={{ fontSize: 11, fontFamily: 'IBM Plex Mono' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="panel p-5 lg:col-span-3">
            <div className="eyebrow mb-1">Branch-wise Risk View</div>
            <h3 className="font-display text-sm font-semibold text-ink-100 mb-4">Risk Concentration by Branch</h3>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={branchData} barSize={14}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1B253B" vertical={false} />
                <XAxis dataKey="branch" tick={{ fill: '#8793AD', fontSize: 11 }} axisLine={{ stroke: '#293552' }} tickLine={false} />
                <YAxis tick={{ fill: '#8793AD', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: '#121A2B', border: '1px solid #293552', borderRadius: 8, fontSize: 12 }}
                  cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                />
                <Legend wrapperStyle={{ fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
                <Bar dataKey="Low" stackId="a" fill={RISK_COLORS.Low} radius={[0, 0, 0, 0]} />
                <Bar dataKey="Medium" stackId="a" fill={RISK_COLORS.Medium} />
                <Bar dataKey="High" stackId="a" fill={RISK_COLORS.High} />
                <Bar dataKey="Critical" stackId="a" fill={RISK_COLORS.Critical} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="panel p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="eyebrow mb-1">Real-time Feed</div>
              <h3 className="font-display text-sm font-semibold text-ink-100">Recent Alerts</h3>
            </div>
            <Link to="/alerts" className="text-xs text-accent hover:text-accent-glow font-medium">
              View all →
            </Link>
          </div>

          {alerts.length === 0 ? (
            <p className="text-sm text-ink-500 py-6 text-center">No alerts yet. Generate a risk score to trigger the engine.</p>
          ) : (
            <div className="divide-y divide-base-700/60">
              {alerts.slice(0, 5).map((a) => (
                <div key={a.id} className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <RiskBadge level={a.severity} />
                    <div className="min-w-0">
                      <p className="text-sm text-ink-100 truncate">{a.title}</p>
                      <p className="text-xs text-ink-500 truncate">{a.message}</p>
                    </div>
                  </div>
                  <span className="text-[11px] font-mono text-ink-700 shrink-0 ml-3">
                    {new Date(a.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
