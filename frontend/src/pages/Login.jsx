import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ShieldHalf, Loader2, AlertCircle } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('officer@bank.com')
  const [password, setPassword] = useState('Officer@123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await signIn(email, password)
      const dest = location.state?.from?.pathname || '/'
      navigate(dest, { replace: true })
    } catch (err) {
      setError(err?.response?.data?.detail || 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-base-900 bg-grid flex items-center justify-center px-4 relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none" style={{
        background: 'radial-gradient(ellipse 60% 50% at 50% 0%, rgba(34,211,201,0.12), transparent)'
      }} />

      <div className="w-full max-w-sm relative">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-accent/15 border border-accent/30 flex items-center justify-center text-accent mb-4">
            <ShieldHalf size={24} />
          </div>
          <h1 className="font-display text-xl font-semibold text-ink-100">SENTINEL</h1>
          <p className="eyebrow mt-1.5">Fraud & Early Warning System</p>
        </div>

        <form onSubmit={handleSubmit} className="panel p-6 space-y-4">
          <div>
            <label className="label-field">Work email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input-field"
              placeholder="officer@bank.com"
            />
          </div>
          <div>
            <label className="label-field">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 text-signal-critical text-xs bg-signal-critical/10 border border-signal-critical/25 rounded-lg px-3 py-2.5">
              <AlertCircle size={14} />
              {error}
            </div>
          )}

          <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
            {loading ? <Loader2 size={16} className="animate-spin" /> : null}
            {loading ? 'Signing in…' : 'Sign in'}
          </button>

          <p className="text-[11px] text-ink-700 text-center pt-1">
            Demo credentials pre-filled — run <code className="font-mono">seed_data.py</code> on the backend first.
          </p>
        </form>
      </div>
    </div>
  )
}
