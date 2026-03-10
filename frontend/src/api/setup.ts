import client from './client'

export interface SetupStatusResponse {
  setup_required: boolean
}

export interface SetupRequest {
  name: string
  timezone: string
}

export interface SetupLocation {
  id: number
  name: string
  timezone: string
  is_active: boolean
}

export const setupApi = {
  getStatus: async (): Promise<SetupStatusResponse> => {
    const response = await client.get('/setup/status')
    return response.data
  },

  create: async (payload: SetupRequest): Promise<SetupLocation> => {
    const response = await client.post('/setup', payload)
    return response.data
  },
}
