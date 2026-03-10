import { create } from 'zustand'

export interface User {
  id: number
  username: string
  role: string
}

export type SetupStatus = 'unknown' | 'required' | 'complete'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  setupStatus: SetupStatus

  login: (user: User, accessToken: string, refreshToken: string) => void
  logout: () => void
  setAuth: (user: User, accessToken: string, refreshToken: string) => void
  setAccessToken: (accessToken: string) => void
  setSetupStatus: (setupRequired: boolean) => void
  resetSetupStatus: () => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  setupStatus: 'unknown',

  login: (user, accessToken, refreshToken) =>
    set({
      user,
      accessToken,
      refreshToken,
      isAuthenticated: true,
      setupStatus: 'unknown',
    }),

  logout: () =>
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      setupStatus: 'unknown',
    }),

  setAuth: (user, accessToken, refreshToken) =>
    set({
      user,
      accessToken,
      refreshToken,
      isAuthenticated: true,
      setupStatus: 'unknown',
    }),

  setAccessToken: (accessToken) => set({ accessToken }),

  setSetupStatus: (setupRequired) =>
    set({ setupStatus: setupRequired ? 'required' : 'complete' }),

  resetSetupStatus: () => set({ setupStatus: 'unknown' }),

  clearAuth: () =>
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      setupStatus: 'unknown',
    }),
}))
