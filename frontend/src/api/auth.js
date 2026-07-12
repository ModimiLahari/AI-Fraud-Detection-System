import client from './client'

export async function login(email, password) {
  const form = new URLSearchParams()
  form.append('username', email)
  form.append('password', password)
  const res = await client.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return res.data
}

export async function register(payload) {
  const res = await client.post('/auth/register', payload)
  return res.data
}

export async function getMe() {
  const res = await client.get('/auth/me')
  return res.data
}
