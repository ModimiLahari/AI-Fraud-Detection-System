import React, { useState } from 'react'
import { Sparkles, Send, Loader2 } from 'lucide-react'
import { askAIAssistant } from '../api/fraud'

const SUGGESTIONS = [
  'Why is this customer high risk?',
  'What should I do next?',
  'Is the cash withdrawal pattern serious?',
]

export default function AIAssistantPanel({ customerId }) {
  const [messages, setMessages] = useState([
    { role: 'ai', text: "Ask me anything about this customer's risk profile — I'll answer using the latest fraud report." },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  async function send(question) {
    const q = question || input
    if (!q.trim()) return
    setMessages((m) => [...m, { role: 'user', text: q }])
    setInput('')
    setLoading(true)
    try {
      const res = await askAIAssistant(customerId, q)
      setMessages((m) => [...m, { role: 'ai', text: res.answer }])
    } catch (err) {
      setMessages((m) => [...m, { role: 'ai', text: 'Could not reach the AI engine. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel p-5 flex flex-col h-full">
      <div className="flex items-center gap-2 mb-1">
        <Sparkles size={15} className="text-accent" />
        <h3 className="font-display text-sm font-semibold text-ink-100">AI Risk Assistant</h3>
      </div>
      <p className="eyebrow mb-4">Ask why, ask what next</p>

      <div className="flex-1 space-y-3 overflow-y-auto mb-4 max-h-64 pr-1">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`text-sm rounded-xl px-3.5 py-2.5 max-w-[90%] ${
              m.role === 'ai'
                ? 'bg-base-700/50 text-ink-300 mr-auto'
                : 'bg-accent/15 text-ink-100 ml-auto border border-accent/25'
            }`}
          >
            {m.text}
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-ink-500 text-xs">
            <Loader2 size={13} className="animate-spin" /> Thinking…
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-1.5 mb-3">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => send(s)}
            className="text-[11px] px-2.5 py-1 rounded-full border border-base-600 text-ink-500 hover:border-accent/50 hover:text-ink-100 transition-colors"
          >
            {s}
          </button>
        ))}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          send()
        }}
        className="flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question…"
          className="input-field text-sm"
        />
        <button type="submit" disabled={loading} className="btn-primary px-3.5">
          <Send size={15} />
        </button>
      </form>
    </div>
  )
}
