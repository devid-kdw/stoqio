import { describe, it, expect } from 'vitest'
import axios from 'axios'
import {
  isNetworkOrServerError,
  getApiErrorBody,
  getApiErrorBodyAsync,
  runWithRetry,
} from './http'

describe('http utilities', () => {
  describe('isNetworkOrServerError', () => {
    it('returns false for non-axios errors', () => {
      expect(isNetworkOrServerError(new Error('normal error'))).toBe(false)
      expect(isNetworkOrServerError(null)).toBe(false)
    })

    it('returns true for network errors (no response)', () => {
      const error = new axios.AxiosError('Network Error')
      expect(isNetworkOrServerError(error)).toBe(true)
    })

    it('returns false for 4xx errors', () => {
      const error = new axios.AxiosError('Bad Request')
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      error.response = { status: 400, data: {}, statusText: '', headers: {}, config: {} as any }
      expect(isNetworkOrServerError(error)).toBe(false)
    })

    it('returns true for 5xx errors', () => {
      const error = new axios.AxiosError('Server Error')
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      error.response = { status: 500, data: {}, statusText: '', headers: {}, config: {} as any }
      expect(isNetworkOrServerError(error)).toBe(true)
    })
  })

  describe('getApiErrorBody', () => {
    it('returns null for non-axios errors', () => {
      expect(getApiErrorBody(new Error())).toBeNull()
    })

    it('returns the data payload for standard errors', () => {
      const error = new axios.AxiosError('Error')
      const payload = { message: 'Business rule failed' }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      error.response = { status: 400, data: payload, statusText: '', headers: {}, config: {} as any }
      expect(getApiErrorBody(error)).toEqual(payload)
    })
  })

  describe('getApiErrorBodyAsync', () => {
    it('returns null for non-axios errors', async () => {
      expect(await getApiErrorBodyAsync(new Error())).toBeNull()
    })

    it('parses blob JSON correctly', async () => {
      const payload = { message: 'Blob business error' }
      const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' })
      const error = new axios.AxiosError('Error')
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      error.response = { status: 400, data: blob, statusText: '', headers: {}, config: {} as any }
      
      const result = await getApiErrorBodyAsync(error)
      expect(result).toEqual(payload)
    })

    it('returns null on malformed blob JSON', async () => {
      const blob = new Blob(['not-json'], { type: 'application/json' })
      const error = new axios.AxiosError('Error')
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      error.response = { status: 400, data: blob, statusText: '', headers: {}, config: {} as any }
      
      const result = await getApiErrorBodyAsync(error)
      expect(result).toBeNull()
    })
  })

  describe('runWithRetry', () => {
    it('executes successfully on first try', async () => {
      let attempts = 0
      const fn = async () => {
        attempts++
        return 'success'
      }
      
      const result = await runWithRetry(fn)
      expect(result).toBe('success')
      expect(attempts).toBe(1)
    })

    it('retries exactly once on network error', async () => {
      let attempts = 0
      const fn = async () => {
        attempts++
        if (attempts === 1) {
          throw new axios.AxiosError('Network Error')
        }
        return 'success'
      }
      
      const result = await runWithRetry(fn)
      expect(result).toBe('success')
      expect(attempts).toBe(2)
    })

    it('does not retry on 400 error', async () => {
      let attempts = 0
      const fn = async () => {
        attempts++
        const error = new axios.AxiosError('Bad Request')
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        error.response = { status: 400, data: {}, statusText: '', headers: {}, config: {} as any }
        throw error
      }
      
      await expect(runWithRetry(fn)).rejects.toThrow('Bad Request')
      expect(attempts).toBe(1)
    })
  })
})
