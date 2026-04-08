import axios from 'axios'
import { authApi } from './auth'
import { getStoredRefreshToken, useAuthStore } from '../store/authStore'
import i18n from '../i18n'

const SUPPORTED_LANGUAGES = ['hr', 'en', 'de', 'hu'] as const
type SupportedLanguage = typeof SUPPORTED_LANGUAGES[number]

function getAcceptLanguage(): SupportedLanguage {
  const tag = i18n.language?.split('-')[0]?.toLowerCase()
  return (SUPPORTED_LANGUAGES as readonly string[]).includes(tag ?? '')
    ? (tag as SupportedLanguage)
    : 'hr'
}

const client = axios.create({
  baseURL: '/api/v1',
})

// Request interceptor — attach bearer token and active UI language
client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  config.headers['Accept-Language'] = getAcceptLanguage()
  return config
})

let refreshPromise: Promise<string> | null = null
let failedQueue: Array<{ resolve: (token: string) => void; reject: (err: unknown) => void }> = []

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else if (token) {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

const forceLoginRedirect = () => {
  if (window.location.pathname !== '/login') {
    window.location.assign('/login')
  }
}

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && originalRequest) {
      // Guard against infinite loops on authn/authz endpoints
      if (
        originalRequest.url?.includes('/auth/login') ||
        originalRequest.url?.includes('/auth/refresh') ||
        originalRequest.url?.includes('/auth/logout')
      ) {
        return Promise.reject(error)
      }

      if (!originalRequest._retry) {
        originalRequest._retry = true

        if (refreshPromise !== null) {
          // A refresh is already in flight — await it instead of starting another
          try {
            const token = await refreshPromise
            originalRequest.headers.Authorization = `Bearer ${token}`
            return client(originalRequest)
          } catch (err) {
            return Promise.reject(err)
          }
        }

        const refreshToken = useAuthStore.getState().refreshToken ?? getStoredRefreshToken()

        if (!refreshToken) {
          useAuthStore.getState().logout()
          forceLoginRedirect()
          return Promise.reject(error)
        }

        if (useAuthStore.getState().refreshToken !== refreshToken) {
          useAuthStore.getState().hydrateRefreshToken(refreshToken)
        }

        refreshPromise = authApi.refresh(refreshToken)
          .then((data) => {
            const newAccessToken = data.access_token
            useAuthStore.getState().setAccessToken(newAccessToken)
            processQueue(null, newAccessToken)
            return newAccessToken
          })
          .catch((refreshError) => {
            processQueue(refreshError, null)
            useAuthStore.getState().logout()
            forceLoginRedirect()
            throw refreshError
          })
          .finally(() => {
            refreshPromise = null
          })

        try {
          const newAccessToken = await refreshPromise
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
          return client(originalRequest)
        } catch (refreshError) {
          return Promise.reject(refreshError)
        }
      }
    }
    return Promise.reject(error)
  }
)

export default client
