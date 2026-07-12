import React, { useEffect, useState } from 'react'
import { Plus, Search, ShieldCheck, ShieldX } from 'lucide-react'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'
import Topbar from '../components/Topbar'
import Modal from '../components/Modal'
import LoadingSpinner from '../components/LoadingSpinner'
import { listCustomers, createCustomer } from '../api/customer'

const emptyForm = {
  customer_code: '', full_name: '', email: '', phone: '',
  pan_number: '', aadhaar_number: '', branch: 'Main Branch', gst_number: '', kyc_verified: true,
}

export default function Customers() {
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const navigate = useNavigate()

  function load() {
    setLoading(true)
    listCustomers().then(setCustomers).finally(() => setLoading(false))
  }

  useEffect(load, [])

  async function handleCreate(e) {
    e.preventDefault()
    setSaving(true)
    try {
      await createCustomer(form)
      toast.success('Customer created')
      setShowModal(false)
      setForm(emptyForm)
      load()
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to create customer')
    } finally {
      setSaving(false)
    }
  }

  const filtered = customers.filter(
    (c) =>
      c.full_name.toLowerCase().includes(search.toLowerCase()) ||
      c.customer_code.toLowerCase().includes(search.toLowerCase()) ||
      c.branch.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <>
      <Topbar title="Customers" subtitle="Manage customer profiles linked to loans & transactions" />
      <div className="p-6 space-y-5">
        <div className="flex items-center justify-between gap-4">
          <div className="relative w-full max-w-sm">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-700" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search name, code, or branch…"
              className="input-field pl-9"
            />
          </div>
          <button onClick={() => setShowModal(true)} className="btn-primary">
            <Plus size={16} /> New Customer
          </button>
        </div>

        {loading ? (
          <LoadingSpinner />
        ) : (
          <div className="panel overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-base-700/60 text-ink-500 text-xs font-mono uppercase tracking-wide">
                  <th className="px-5 py-3 font-medium">Code</th>
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-5 py-3 font-medium">Branch</th>
                  <th className="px-5 py-3 font-medium">KYC</th>
                  <th className="px-5 py-3 font-medium">GST</th>
                  <th className="px-5 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-base-700/40">
                {filtered.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/customers/${c.id}`)}
                    className="cursor-pointer hover:bg-base-700/20 transition-colors"
                  >
                    <td className="px-5 py-3.5 font-mono text-ink-300">{c.customer_code}</td>
                    <td className="px-5 py-3.5 text-ink-100 font-medium">{c.full_name}</td>
                    <td className="px-5 py-3.5 text-ink-500">{c.branch}</td>
                    <td className="px-5 py-3.5">
                      {c.kyc_verified ? (
                        <span className="inline-flex items-center gap-1 text-signal-low text-xs">
                          <ShieldCheck size={14} /> Verified
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-signal-critical text-xs">
                          <ShieldX size={14} /> Pending
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 font-mono text-ink-500 text-xs">{c.gst_number || '—'}</td>
                    <td className="px-5 py-3.5 text-right text-accent text-xs font-medium">View →</td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={6} className="text-center text-ink-500 py-10 text-sm">
                      No customers found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <Modal title="Add New Customer" onClose={() => setShowModal(false)}>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label-field">Customer Code *</label>
                <input required className="input-field" value={form.customer_code}
                  onChange={(e) => setForm({ ...form, customer_code: e.target.value })} placeholder="CUST1006" />
              </div>
              <div>
                <label className="label-field">Branch</label>
                <input className="input-field" value={form.branch}
                  onChange={(e) => setForm({ ...form, branch: e.target.value })} />
              </div>
            </div>
            <div>
              <label className="label-field">Full Name *</label>
              <input required className="input-field" value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label-field">Email</label>
                <input type="email" className="input-field" value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </div>
              <div>
                <label className="label-field">Phone</label>
                <input className="input-field" value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label-field">PAN Number</label>
                <input className="input-field" value={form.pan_number}
                  onChange={(e) => setForm({ ...form, pan_number: e.target.value })} />
              </div>
              <div>
                <label className="label-field">GST Number</label>
                <input className="input-field" value={form.gst_number}
                  onChange={(e) => setForm({ ...form, gst_number: e.target.value })} />
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm text-ink-300">
              <input type="checkbox" checked={form.kyc_verified}
                onChange={(e) => setForm({ ...form, kyc_verified: e.target.checked })}
                className="rounded border-base-600 bg-base-900 text-accent focus:ring-accent/40" />
              KYC Verified
            </label>
            <button type="submit" disabled={saving} className="btn-primary w-full">
              {saving ? 'Creating…' : 'Create Customer'}
            </button>
          </form>
        </Modal>
      )}
    </>
  )
}
