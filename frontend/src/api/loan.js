import client from './client'

export const listLoans = () => client.get('/loan/list').then((r) => r.data)
export const getLoansForCustomer = (customerId) =>
  client.get(`/loan/customer/${customerId}`).then((r) => r.data)
export const createLoan = (payload) => client.post('/loan/create', payload).then((r) => r.data)
export const updateLoan = (id, payload) => client.put(`/loan/${id}`, payload).then((r) => r.data)
export const deleteLoan = (id) => client.delete(`/loan/${id}`).then((r) => r.data)
