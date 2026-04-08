import axios from 'axios'

export interface ApiErrorBody {
  error?: string
  message?: string
  details?: Record<string, unknown>
}

export const CONNECTION_ERROR_MESSAGE =
  'Greška povezivanja. Provjeri je li server pokrenut i pokušaj ponovno.'

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

export async function getApiErrorBodyAsync(error: unknown): Promise<ApiErrorBody | null> {
  if (!axios.isAxiosError(error)) {
    return null
  }

  const responseData = error.response?.data
  if (!responseData) {
    return null
  }

  if (responseData instanceof Blob) {
    try {
      const parsed = JSON.parse(await responseData.text()) as ApiErrorBody
      return parsed
    } catch {
      return null
    }
  }

  return responseData as ApiErrorBody
}

const TECHNICAL_KEYWORDS = [
  "constraint", "column", "database", "traceback", "Exception:",
  "Error:", "sqlalchemy", "psycopg", "integrity", "syntax error",
  "relation", "DETAIL:", "HINT:"
]

export function getDisplayError(err: unknown, fallback: string): string {
  const body = getApiErrorBody(err)
  const message = body?.message
  if (!message) return fallback
  const lowerMsg = message.toLowerCase()
  if (TECHNICAL_KEYWORDS.some(kw => lowerMsg.includes(kw.toLowerCase()))) {
    return fallback
  }
  return message
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
