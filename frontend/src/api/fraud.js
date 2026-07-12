import client, { API_BASE_URL } from './client'

export const generateScore = (customerId) =>
  client.post('/fraud/generate-score', { customer_id: customerId }).then((r) => r.data)

export const checkLoanApplication = (customerId, loanId) =>
  client.post('/fraud/check-loan-application', { customer_id: customerId, loan_id: loanId }).then((r) => r.data)

export const checkTransaction = (customerId, transactionId) =>
  client
    .post('/fraud/check-transaction', { customer_id: customerId, transaction_id: transactionId })
    .then((r) => r.data)

export const getLatestReport = (customerId) =>
  client.get(`/fraud/report/${customerId}`).then((r) => r.data)

export const getReportHistory = (customerId) =>
  client.get(`/fraud/report/${customerId}/history`).then((r) => r.data)

export const getReasons = (customerId) =>
  client.get(`/fraud/reasons/${customerId}`).then((r) => r.data)

export const getAlerts = () => client.get('/fraud/alerts').then((r) => r.data)

export const markAlertRead = (alertId) =>
  client.put(`/fraud/alerts/${alertId}/read`).then((r) => r.data)

export const getDashboardSummary = () =>
  client.get('/fraud/dashboard-summary').then((r) => r.data)

export const askAIAssistant = (customerId, question) =>
  client.post(`/fraud/ai-assistant/${customerId}`, { question }).then((r) => r.data)

export function pdfReportUrl(customerId) {
  return `${API_BASE_URL}/fraud/report/${customerId}/pdf`
}

export function excelReportUrl() {
  return `${API_BASE_URL}/fraud/report/excel/all`
}

export async function downloadWithAuth(url, filename) {
  const token = localStorage.getItem('sentinel_token')
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) throw new Error('Download failed')
  const blob = await res.blob()
  const link = document.createElement('a')
  link.href = window.URL.createObjectURL(blob)
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
}
