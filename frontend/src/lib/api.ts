import axios from 'axios'

// Базовый HTTP-клиент React-админки. baseURL = тот же origin (панель рядом с API
// за nginx клуба). NOTE: пути freeze/unfreeze/wallet/selfservice/qr — сверить с
// OpenAPI при первом запуске панели (админка опциональна, сборка — критерий FIX3).
const api = axios.create({ baseURL: '/api/v1' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    ;(config.headers as any).Authorization = 'Bearer ' + token
  }
  return config
})

export const authApi = {
  login: (login: string, password: string) => api.post('/auth/login', { login, password }),
  me: () => api.get('/users/me'),
}

export const clientsApi = {
  list: (params?: any) => api.get('/clients/', { params }),
  create: (data?: any) => api.post('/clients/', data),
}

export const visitsApi = {
  entry: (data?: any) => api.post('/visits/entry', data),
  exit: (data?: any) => api.post('/visits/exit', data),
  active: () => api.get('/visits/active'),
  statsToday: () => api.get('/analytics/visits/today'),
}

export const subscriptionsApi = {
  list: (params?: any) => api.get('/subscriptions', { params }),
  freeze: (payload?: any) => api.post('/subscriptions/freeze', payload),
  unfreeze: (payload?: any) => api.post('/subscriptions/unfreeze', payload),
  cancel: (payload?: any) => api.post('/subscriptions/cancel', payload),
  renew: (payload?: any) => api.post('/subscriptions/renew', payload),
}

export const analyticsApi = {
  dashboard: () => api.get('/analytics/dashboard'),
  visits: (params?: any) => api.get('/analytics/visits', { params }),
}

export const financeApi = {
  payments: (params?: any) => api.get('/payments', { params }),
  walletMe: () => api.get('/finance/wallet/me'),
  walletTransactions: () => api.get('/finance/wallet/transactions'),
}

export const devicesApi = {
  list: () => api.get('/devices'),
  ping: (payload?: any) => api.post('/devices/ping', payload),
}

export const accessApi = {
  check: (data?: any) => api.post('/skud/checkaccess', data),
  grant: (data?: any) => api.post('/access/grant', data),
  qrCreate: (data?: any) => api.post('/qr/create', data),
  qrGet: (id: any) => api.get('/qr/' + id),
}

export const selfserviceApi = {
  profile: () => api.get('/selfservice/profile'),
  subscriptions: () => api.get('/selfservice/subscriptions'),
  visits: () => api.get('/selfservice/visits'),
}

export default api
