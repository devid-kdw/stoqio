import axios from 'axios'

export interface ApiErrorBody {
  error?: string
  message?: string
  details?: Record<string, unknown>
}

export const CONNECTION_ERROR_MESSAGE =
  'Connection error. Please check that the server is running and try again.'

export function isNetworkOrServerError(error: unknown): boolean {
  if (!axios.isAxiosError(error)) {
    return false
  }

  if (!error.response) {
    return true
  }

  return error.response.status >= 500
}

export function getApiErrorBody(error: unknown): ApiErrorBody | null {
  if (!axios.isAxiosError<ApiErrorBody>(error)) {
    return null
  }

  return error.response?.data ?? null
}

export async function runWithRetry<T>(request: () => Promise<T>): Promise<T> {
  try {
    return await request()
  } catch (error) {
    if (!isNetworkOrServerError(error)) {
      throw error
    }

    return request()
  }
}
