import React, { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Zap, Download, Plus, TrendingUp, CheckCircle2, Sparkles, Loader2 } from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import Topbar from '../components/Topbar'
import RiskGauge from '../components/RiskGauge'
import RiskBadge from '../components/RiskBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import Modal from '../components/Modal'
import AIAssistantPanel from '../components/AIAssistantPanel'
import { getCustomer } from '../api/customer'
import { getLoansForCustomer, createLoan } from '../api/loan'
import { getTransactionsForCustomer, createTransaction } from '../api/transaction'
import {
  generateScore, getLatestReport, getReportHistory, getReasons,
  pdfReportUrl, downloadWithAuth, askAIAssistant,
} from '../api/fraud'

const emptyLoan = {
  loan_amount: '', loan_type: 'Personal Loan', emi_amount: '', emi_due_date: 5,
  tenure_months: 12, emi_bounce_count: 0, delayed_repayment_count: 0, loan_enquiry_count_last_30_days: 0,
}
const emptyTxn = {
  txn_type: 'debit', amount: '', balance_after: '', beneficiary: '',
  beneficiary_flagged: false, gst_declared_turnover: '', is_cash_withdrawal_post_disbursement: false,
}

export default function CustomerDetail() {
  const { id } = useParams()
  const customerId = Number(id)

  const [customer, setCustomer] = useState(null)
  const [loans, setLoans] = useState([])
  const [transactions, setTransactions] = useState([])
  const [report, setReport] = useState(null)
  const [reasons, setReasons] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [scoring, setScoring] = useState(false)
  const [loanModal, setLoanModal] = useState(false)
  const [txnModal, setTxnModal] = useState(false)
  const [loanForm, setLoanForm] = useState(emptyLoan)
  const [txnForm, setTxnForm] = useState(emptyTxn)
  const [whyModal, setWhyModal] = useState(false)
  const [whyLoading, setWhyLoading] = useState(false)
  const [whyAnswer, setWhyAnswer] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [c, l, t] = await Promise.all([
        getCustomer(customerId),
        getLoansForCustomer(customerId),
        getTransactionsForCustomer(customerId),
      ])
      setCustomer(c)
      setLoans(l)
      setTransactions(t)
      try {
        const [r, rs, h] = await Promise.all([
          getLatestReport(customerId),
          getReasons(customerId),
          getReportHistory(customerId),
        ])
        setReport(r)
        setReasons(rs)
        setHistory(h)
      } catch {
        setReport(null)
      }
    } finally {
      setLoading(false)
    }
  }, [customerId])

  useEffect(() => { load() }, [load])

  async function handleGenerateScore() {
    setScoring(true)
    try {
      await generateScore(customerId)
      toast.success('Risk score generated')
      await load()
    } catch (err) {
      toast.error('Failed to generate score')
    } finally {
      setScoring(false)
    }
  }

  async function handleAddLoan(e) {
    e.preventDefault()
    try {
      await createLoan({ ...loanForm, customer_id: customerId })
      toast.success('Loan added')
      setLoanModal(false)
      setLoanForm(emptyLoan)
      load()
    } catch {
      toast.error('Failed to add loan')
    }
  }

  async function handleAddTxn(e) {
    e.preventDefault()
    try {
      await createTransaction({ ...txnForm, customer_id: customerId })
      toast.success('Transaction added')
      setTxnModal(false)
      setTxnForm(emptyTxn)
      load()
    } catch {
      toast.error('Failed to add transaction')
    }
  }

  async function handleDownloadPdf() {
    try {
      await downloadWithAuth(pdfReportUrl(customerId), `fraud_report_${customer.customer_code}.pdf`)
    } catch {
      toast.error('Generate a score first, then download')
    }
  }

  async function handleWhyHighRisk() {
    setWhyModal(true)
    setWhyLoading(true)
    try {
      const res = await askAIAssistant(customerId, 'Why is this customer high risk?')
      setWhyAnswer(res.answer)
    } catch {
      setWhyAnswer('Could not reach the AI engine. Please try again.')
    } finally {
      setWhyLoading(false)
    }
  }

  if (loading) return <LoadingSpinner label="Loading customer…" />
  if (!customer) return null

  const trendData = history.map((h, i) => ({
    idx: i + 1,
    score: h.risk_score,
    date: new Date(h.generated_at).toLocaleDateString(),
  }))

  return (
    <>
      <Topbar title={customer.full_name} subtitle={`${customer.customer_code} · ${customer.branch}`} />
      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Risk Gauge + actions */}
          <div className="panel p-5 flex flex-col items-center">
            <div className="eyebrow mb-3 self-start">Current Risk Score</div>
            <RiskGauge score={report?.risk_score || 0} />
            <div className="flex gap-2 w-full mt-4">
              <button onClick={handleGenerateScore} disabled={scoring} className="btn-primary flex-1">
                <Zap size={15} /> {scoring ? 'Scoring…' : 'Generate Score'}
              </button>
              <button onClick={handleDownloadPdf} className="btn-ghost" title="Download PDF report">
                <Download size={15} />
              </button>
            </div>
            <button
              onClick={handleWhyHighRisk}
              disabled={!report}
              className="btn-ghost w-full mt-2 !justify-center disabled:opacity-30"
              title={report ? 'Ask AI why this customer is high risk' : 'Generate a score first'}
            >
              <Sparkles size={14} className="text-accent" /> Why is this customer High Risk?
            </button>
          </div>

          {/* Trend chart */}
          <div className="panel p-5 lg:col-span-2">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp size={14} className="text-accent" />
              <div className="eyebrow">Risk Trend</div>
            </div>
            <h3 className="font-display text-sm font-semibold text-ink-100 mb-4">Score History Over Time</h3>
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1B253B" vertical={false} />
                  <XAxis dataKey="date" tick={{ fill: '#8793AD', fontSize: 10 }} axisLine={{ stroke: '#293552' }} tickLine={false} />
                  <YAxis domain={[0, 100]} tick={{ fill: '#8793AD', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: '#121A2B', border: '1px solid #293552', borderRadius: 8, fontSize: 12 }} />
                  <Line type="monotone" dataKey="score" stroke="#22D3C9" strokeWidth={2} dot={{ r: 3, fill: '#22D3C9' }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[180px] flex items-center justify-center text-ink-500 text-sm">
                No score history yet — click "Generate Score" to begin tracking.
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Triggered rules + explanation + recommendations */}
          <div className="lg:col-span-2 space-y-5">
            <div className="panel p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="eyebrow mb-1">Rule Engine Output</div>
                  <h3 className="font-display text-sm font-semibold text-ink-100">Triggered Risk Signals</h3>
                </div>
                {report && <RiskBadge level={report.risk_level} />}
              </div>
              {!reasons || reasons.reasons.length === 0 ? (
                <p className="text-sm text-ink-500 py-4">
                  {report ? 'No risk rules triggered — account looks healthy.' : 'Generate a score to see triggered rules.'}
                </p>
              ) : (
                <div className="space-y-2.5">
                  {reasons.reasons.map((r, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-base-900/60 border border-base-700/50">
                      <span className="font-mono text-xs font-semibold text-signal-high shrink-0 mt-0.5">+{r.points}</span>
                      <div>
                        <div className="text-xs font-mono text-ink-500 mb-0.5">{r.rule}</div>
                        <p className="text-sm text-ink-300">{r.reason}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {report?.ai_explanation && (
              <div className="panel p-5">
                <div className="eyebrow mb-1">AI Explanation</div>
                <h3 className="font-display text-sm font-semibold text-ink-100 mb-3">Plain-English Summary</h3>
                <p className="text-sm text-ink-300 leading-relaxed">{report.ai_explanation}</p>
              </div>
            )}

            {reasons?.recommended_actions?.length > 0 && (
              <div className="panel p-5">
                <div className="eyebrow mb-1">Next Steps</div>
                <h3 className="font-display text-sm font-semibold text-ink-100 mb-3">Recommended Actions</h3>
                <div className="space-y-2">
                  {reasons.recommended_actions.map((a, i) => (
                    <div key={i} className="flex items-start gap-2.5 text-sm text-ink-300">
                      <CheckCircle2 size={15} className="text-signal-low shrink-0 mt-0.5" />
                      {a}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* AI Assistant */}
          <AIAssistantPanel customerId={customerId} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Loans */}
          <div className="panel p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display text-sm font-semibold text-ink-100">Loans</h3>
              <button onClick={() => setLoanModal(true)} className="btn-ghost !py-1.5 !px-3 text-xs">
                <Plus size={13} /> Add Loan
              </button>
            </div>
            <div className="space-y-2.5">
              {loans.map((l) => (
                <div key={l.id} className="p-3 rounded-lg bg-base-900/60 border border-base-700/50 text-sm">
                  <div className="flex justify-between">
                    <span className="text-ink-100 font-medium">{l.loan_type}</span>
                    <span className="font-mono text-accent">₹{l.loan_amount.toLocaleString('en-IN')}</span>
                  </div>
                  <div className="flex gap-4 mt-1.5 text-xs text-ink-500">
                    <span>EMI bounces: {l.emi_bounce_count}</span>
                    <span>Enquiries: {l.loan_enquiry_count_last_30_days}</span>
                    <span>Status: {l.status}</span>
                  </div>
                </div>
              ))}
              {loans.length === 0 && <p className="text-sm text-ink-500 py-2">No loans on record.</p>}
            </div>
          </div>

          {/* Transactions */}
          <div className="panel p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display text-sm font-semibold text-ink-100">Transactions</h3>
              <button onClick={() => setTxnModal(true)} className="btn-ghost !py-1.5 !px-3 text-xs">
                <Plus size={13} /> Add Transaction
              </button>
            </div>
            <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
              {transactions.map((t) => (
                <div key={t.id} className="p-3 rounded-lg bg-base-900/60 border border-base-700/50 text-sm flex justify-between items-center">
                  <div>
                    <span className="text-ink-100 capitalize">{t.txn_type.replace('_', ' ')}</span>
                    {t.beneficiary_flagged && <span className="ml-2 text-[10px] text-signal-critical font-mono">FLAGGED</span>}
                    <div className="text-xs text-ink-500">{new Date(t.txn_date).toLocaleDateString()}</div>
                  </div>
                  <span className="font-mono text-ink-300">₹{t.amount.toLocaleString('en-IN')}</span>
                </div>
              ))}
              {transactions.length === 0 && <p className="text-sm text-ink-500 py-2">No transactions on record.</p>}
            </div>
          </div>
        </div>
      </div>

      {whyModal && (
        <Modal title="Why is this customer High Risk?" onClose={() => setWhyModal(false)}>
          {whyLoading ? (
            <div className="flex items-center gap-2 text-ink-500 text-sm py-6 justify-center">
              <Loader2 size={16} className="animate-spin" /> Asking Gemini…
            </div>
          ) : (
            <div className="flex items-start gap-2.5 text-sm text-ink-200 leading-relaxed">
              <Sparkles size={16} className="text-accent shrink-0 mt-0.5" />
              <p>{whyAnswer}</p>
            </div>
          )}
        </Modal>
      )}

      {loanModal && (
        <Modal title="Add Loan" onClose={() => setLoanModal(false)}>
          <form onSubmit={handleAddLoan} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label-field">Loan Amount *</label>
                <input required type="number" className="input-field" value={loanForm.loan_amount}
                  onChange={(e) => setLoanForm({ ...loanForm, loan_amount: Number(e.target.value) })} />
              </div>
              <div>
                <label className="label-field">Loan Type</label>
                <select className="input-field" value={loanForm.loan_type}
                  onChange={(e) => setLoanForm({ ...loanForm, loan_type: e.target.value })}>
                  <option>Personal Loan</option>
                  <option>Business Loan</option>
                  <option>MSME Loan</option>
                  <option>Vehicle Loan</option>
                  <option>Home Loan</option>
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label-field">EMI Amount</label>
                <input type="number" className="input-field" value={loanForm.emi_amount}
                  onChange={(e) => setLoanForm({ ...loanForm, emi_amount: Number(e.target.value) })} />
              </div>
              <div>
                <label className="label-field">Tenure (months)</label>
                <input type="number" className="input-field" value={loanForm.tenure_months}
                  onChange={(e) => setLoanForm({ ...loanForm, tenure_months: Number(e.target.value) })} />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="label-field">EMI Bounces</label>
                <input type="number" className="input-field" value={loanForm.emi_bounce_count}
                  onChange={(e) => setLoanForm({ ...loanForm, emi_bounce_count: Number(e.target.value) })} />
              </div>
              <div>
                <label className="label-field">Delayed Repay.</label>
                <input type="number" className="input-field" value={loanForm.delayed_repayment_count}
                  onChange={(e) => setLoanForm({ ...loanForm, delayed_repayment_count: Number(e.target.value) })} />
              </div>
              <div>
                <label className="label-field">Enquiries/30d</label>
                <input type="number" className="input-field" value={loanForm.loan_enquiry_count_last_30_days}
                  onChange={(e) => setLoanForm({ ...loanForm, loan_enquiry_count_last_30_days: Number(e.target.value) })} />
              </div>
            </div>
            <button type="submit" className="btn-primary w-full">Add Loan</button>
          </form>
        </Modal>
      )}

      {txnModal && (
        <Modal title="Add Transaction" onClose={() => setTxnModal(false)}>
          <form onSubmit={handleAddTxn} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label-field">Type</label>
                <select className="input-field" value={txnForm.txn_type}
                  onChange={(e) => setTxnForm({ ...txnForm, txn_type: e.target.value })}>
                  <option value="credit">Credit</option>
                  <option value="debit">Debit</option>
                  <option value="cash_withdrawal">Cash Withdrawal</option>
                </select>
              </div>
              <div>
                <label className="label-field">Amount *</label>
                <input required type="number" className="input-field" value={txnForm.amount}
                  onChange={(e) => setTxnForm({ ...txnForm, amount: Number(e.target.value) })} />
              </div>
            </div>
            <div>
              <label className="label-field">Beneficiary</label>
              <input className="input-field" value={txnForm.beneficiary}
                onChange={(e) => setTxnForm({ ...txnForm, beneficiary: e.target.value })} />
            </div>
            <div>
              <label className="label-field">GST Declared Turnover (optional)</label>
              <input type="number" className="input-field" value={txnForm.gst_declared_turnover}
                onChange={(e) => setTxnForm({ ...txnForm, gst_declared_turnover: Number(e.target.value) })} />
            </div>
            <div className="flex gap-6">
              <label className="flex items-center gap-2 text-sm text-ink-300">
                <input type="checkbox" checked={txnForm.beneficiary_flagged}
                  onChange={(e) => setTxnForm({ ...txnForm, beneficiary_flagged: e.target.checked })}
                  className="rounded border-base-600 bg-base-900 text-accent" />
                Flagged beneficiary
              </label>
              <label className="flex items-center gap-2 text-sm text-ink-300">
                <input type="checkbox" checked={txnForm.is_cash_withdrawal_post_disbursement}
                  onChange={(e) => setTxnForm({ ...txnForm, is_cash_withdrawal_post_disbursement: e.target.checked })}
                  className="rounded border-base-600 bg-base-900 text-accent" />
                Post-disbursement withdrawal
              </label>
            </div>
            <button type="submit" className="btn-primary w-full">Add Transaction</button>
          </form>
        </Modal>
      )}
    </>
  )
}
