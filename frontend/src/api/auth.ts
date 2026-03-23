import axios from 'axios'

const authClient = axios.create({
  baseURL: '/api/v1/auth',
})

export interface LoginResponse {
  access_token: string
  refresh_token: string
  user: {
    id: number
    username: string
    role: string
  }
}

export interface RefreshResponse {
  access_token: string
}

export interface MeResponse {
  id: number
  username: string
  role: string
  is_active: boolean
}

export const authApi = {
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const response = await authClient.post('/login', { username, password })
    return response.data
  },

  refresh: async (refreshToken: string): Promise<RefreshResponse> => {
    const response = await authClient.post('/refresh', {}, {
      headers: {
        Authorization: `Bearer ${refreshToken}`,
      },
    })
    return response.data
  },

  me: async (accessToken?: string): Promise<MeResponse> => {
    const response = await authClient.get(
      '/me',
      accessToken
        ? {
            headers: {
              Authorization: `Bearer ${accessToken}`,
            },
          }
        : undefined,
    )
    return response.data
  },

  logout: async (refreshToken: string) => {
    const response = await authClient.post('/logout', {}, {
      headers: {
        Authorization: `Bearer ${refreshToken}`,
      },
    })
    return response.data
  },
}
