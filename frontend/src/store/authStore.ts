import { create } from 'zustand'

export interface User {
  id: number
  username: string
  role: string
}

export type SetupStatus = 'unknown' | 'required' | 'complete'

export const REFRESH_TOKEN_STORAGE_KEY = 'stoqio_refresh_token'

const persistRefreshToken = (refreshToken: string | null) => {
  if (typeof window === 'undefined') {
    return
  }

  try {
    if (refreshToken) {
      window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, refreshToken)
      return
    }

    window.localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY)
  } catch {
    // Ignore storage failures and keep auth state in memory.
  }
}

export const getStoredRefreshToken = (): string | null => {
  if (typeof window === 'undefined') {
    return null
  }

  try {
    return window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

const getLoggedOutState = () => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  setupStatus: 'unknown' as const,
})

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  setupStatus: SetupStatus

  hydrateRefreshToken: (refreshToken: string | null) => void
  login: (user: User, accessToken: string, refreshToken: string) => void
  logout: () => void
  setAuth: (user: User, accessToken: string, refreshToken: string) => void
  setAccessToken: (accessToken: string) => void
  setSetupStatus: (setupRequired: boolean) => void
  resetSetupStatus: () => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  ...getLoggedOutState(),

  hydrateRefreshToken: (refreshToken) => {
    persistRefreshToken(refreshToken)
    set({ refreshToken })
  },

  login: (user, accessToken, refreshToken) => {
    persistRefreshToken(refreshToken)
    set({
      user,
      accessToken,
      refreshToken,
      isAuthenticated: true,
      setupStatus: 'unknown',
    })
  },

  logout: () => {
    persistRefreshToken(null)
    set(getLoggedOutState())
  },

  setAuth: (user, accessToken, refreshToken) => {
    persistRefreshToken(refreshToken)
    set({
      user,
      accessToken,
      refreshToken,
      isAuthenticated: true,
      setupStatus: 'unknown',
    })
  },

  setAccessToken: (accessToken) => set({ accessToken }),

  setSetupStatus: (setupRequired) =>
    set({ setupStatus: setupRequired ? 'required' : 'complete' }),

  resetSetupStatus: () => set({ setupStatus: 'unknown' }),

  clearAuth: () => {
    persistRefreshToken(null)
    set(getLoggedOutState())
  },
}))
