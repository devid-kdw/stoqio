import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const client = axios.create({
  baseURL: '/api/v1',
})

// Request interceptor — attach bearer token from Zustand auth store
client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor — scaffold for future 401 refresh handling
// TODO (Phase 3 – Auth): implement token refresh flow here.
//   On 401: call POST /api/v1/auth/refresh with refreshToken,
//   update the store with the new access token,
//   then retry the original request.
//   On refresh failure: call clearAuth() and redirect to /login.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Placeholder: refresh flow not implemented in Phase 1.
      // Do not clear auth here — Phase 3 will add retry logic.
    }
    return Promise.reject(error)
  },
)

export default client
