import axios from 'axios'
import { setupApi } from '../api/setup'
import { getHomeRouteForRole } from './roles'

export const DEFAULT_SETUP_TIMEZONE = 'Europe/Berlin'

const FALLBACK_TIMEZONES = [
  DEFAULT_SETUP_TIMEZONE,
  'UTC',
  'Europe/London',
  'Europe/Paris',
  'America/New_York',
  'America/Chicago',
  'America/Los_Angeles',
  'Asia/Dubai',
  'Asia/Singapore',
]

export const getTimezoneOptions = (): string[] => {
  const intlWithSupportedValues = Intl as typeof Intl & {
    supportedValuesOf?: (key: 'timeZone') => string[]
  }

  try {
    const timezones = intlWithSupportedValues.supportedValuesOf?.('timeZone')
    if (!timezones || timezones.length === 0) {
      return FALLBACK_TIMEZONES
    }

    return timezones.includes(DEFAULT_SETUP_TIMEZONE)
      ? timezones
      : [DEFAULT_SETUP_TIMEZONE, ...timezones]
  } catch {
    return FALLBACK_TIMEZONES
  }
}

export const isRetryableSetupRequestError = (error: unknown): boolean => {
  if (!axios.isAxiosError(error)) {
    return true
  }

  return !error.response || error.response.status >= 500
}

export const fetchSetupStatus = async (): Promise<boolean> => {
  try {
    const response = await setupApi.getStatus()
    return response.setup_required
  } catch (error) {
    if (!isRetryableSetupRequestError(error)) {
      throw error
    }

    const response = await setupApi.getStatus()
    return response.setup_required
  }
}

export const getAuthenticatedDestination = (
  role: string | null | undefined,
  setupRequired: boolean,
): string => {
  if (setupRequired && role === 'ADMIN') {
    return '/setup'
  }

  return getHomeRouteForRole(role)
}
