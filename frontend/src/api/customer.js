import client from './client'

export const listCustomers = () => client.get('/customer/list').then((r) => r.data)
export const getCustomer = (id) => client.get(`/customer/${id}`).then((r) => r.data)
export const createCustomer = (payload) => client.post('/customer/create', payload).then((r) => r.data)
export const updateCustomer = (id, payload) => client.put(`/customer/${id}`, payload).then((r) => r.data)
export const deleteCustomer = (id) => client.delete(`/customer/${id}`).then((r) => r.data)
