import client from './client'

export const listTransactions = () => client.get('/transaction/list').then((r) => r.data)
export const getTransactionsForCustomer = (customerId) =>
  client.get(`/transaction/customer/${customerId}`).then((r) => r.data)
export const createTransaction = (payload) => client.post('/transaction/create', payload).then((r) => r.data)
export const deleteTransaction = (id) => client.delete(`/transaction/${id}`).then((r) => r.data)
