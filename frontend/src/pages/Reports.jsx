import React, { useEffect, useState } from 'react'
import { FileDown, FileSpreadsheet } from 'lucide-react'
import toast from 'react-hot-toast'
import { Link } from 'react-router-dom'
import Topbar from '../components/Topbar'
import RiskBadge from '../components/RiskBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import { listCustomers } from '../api/customer'
import { getLatestReport, pdfReportUrl, excelReportUrl, downloadWithAuth } from '../api/fraud'

export default function Reports() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listCustomers().then(async (customers) => {
      const withReports = await Promise.all(
        customers.map(async (c) => {
          try {
            const r = await getLatestReport(c.id)
            return { customer: c, report: r }
          } catch {
            return { customer: c, report: null }
          }
        })
      )
      setRows(withReports)
      setLoading(false)
    })
  }, [])

  async function handlePdf(customer) {
    try {
      await downloadWithAuth(pdfReportUrl(customer.id), `fraud_report_${customer.customer_code}.pdf`)
    } catch {
      toast.error('Generate a score for this customer first')
    }
  }

  async function handleExcelAll() {
    try {
      await downloadWithAuth(excelReportUrl(), 'fraud_report_all_customers.xlsx')
    } catch {
      toast.error('Failed to export')
    }
  }

  return (
    <>
      <Topbar title="Reports" subtitle="Export fraud & risk reports for offline review" />
      <div className="p-6 space-y-5">
        <div className="panel p-5 flex items-center justify-between">
          <div>
            <h3 className="font-display text-sm font-semibold text-ink-100">Portfolio-wide Excel Export</h3>
            <p className="text-xs text-ink-500 mt-1">Download risk scores for every customer as a single spreadsheet.</p>
          </div>
          <button onClick={handleExcelAll} className="btn-primary">
            <FileSpreadsheet size={15} /> Export Excel
          </button>
        </div>

        {loading ? (
          <LoadingSpinner />
        ) : (
          <div className="panel overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-base-700/60 text-ink-500 text-xs font-mono uppercase tracking-wide">
                  <th className="px-5 py-3 font-medium">Customer</th>
                  <th className="px-5 py-3 font-medium">Branch</th>
                  <th className="px-5 py-3 font-medium">Risk Score</th>
                  <th className="px-5 py-3 font-medium">Level</th>
                  <th className="px-5 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-base-700/40">
                {rows.map(({ customer, report }) => (
                  <tr key={customer.id}>
                    <td className="px-5 py-3.5">
                      <Link to={`/customers/${customer.id}`} className="text-ink-100 font-medium hover:text-accent">
                        {customer.full_name}
                      </Link>
                      <div className="text-xs font-mono text-ink-700">{customer.customer_code}</div>
                    </td>
                    <td className="px-5 py-3.5 text-ink-500">{customer.branch}</td>
                    <td className="px-5 py-3.5 font-mono text-ink-300">
                      {report ? `${report.risk_score}/100` : '—'}
                    </td>
                    <td className="px-5 py-3.5">
                      <RiskBadge level={report?.risk_level || 'Not Evaluated'} />
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <button
                        onClick={() => handlePdf(customer)}
                        disabled={!report}
                        className="btn-ghost !py-1.5 !px-3 text-xs disabled:opacity-30"
                      >
                        <FileDown size={13} /> PDF
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}
