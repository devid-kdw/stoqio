/**
 * locale.ts — shared locale-aware formatting helpers.
 *
 * All helpers derive the locale string from the active i18n language at
 * call time. This ensures that after `i18n.changeLanguage(...)` is called,
 * the next render cycle picks up the new locale without requiring any
 * additional store changes.
 *
 * Rules (per Wave 3 Phase 1 contract):
 * - Only locale selection changes here; quantity precision decisions and
 *   timezone semantics stay with the caller.
 * - The mapping is: i18n language tag → BCP-47 locale string.
 *   Unknown tags fall back to 'hr-HR'.
 */

import i18n from '../i18n'

const LANGUAGE_TO_LOCALE: Record<string, string> = {
  hr: 'hr-HR',
  en: 'en-GB',
  de: 'de-DE',
  hu: 'hu-HU',
}

/**
 * Returns the BCP-47 locale string for the currently active i18n language.
 * Falls back to 'hr-HR' for any language tag that is not in the mapping.
 */
export function getActiveLocale(): string {
  const tag = i18n.language?.split('-')[0]?.toLowerCase() ?? 'hr'
  return LANGUAGE_TO_LOCALE[tag] ?? 'hr-HR'
}

/**
 * Formats a date-only ISO string (or any parseable date value) using the
 * active UI locale, with day/month/year presentation.
 *
 * Returns '—' for null/falsy input or unparseable values.
 */
export function formatDate(value: string | null): string {
  if (!value) {
    return '—'
  }

  try {
    return new Date(value).toLocaleDateString(getActiveLocale(), {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
  } catch {
    return '—'
  }
}

/**
 * Formats a datetime ISO string using the active UI locale, including
 * day, month, year, hour and minute (24-hour clock).
 *
 * Returns '—' for null/falsy input or unparseable values.
 */
export function formatDateTime(value: string | null): string {
  if (!value) {
    return '—'
  }

  try {
    return new Date(value).toLocaleString(getActiveLocale(), {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })
  } catch {
    return '—'
  }
}

/**
 * Formats a number with a fixed number of fraction digits using the
 * active UI locale.
 *
 * This helper changes ONLY the locale used for formatting. Callers
 * continue to decide the number of decimal places (quantity precision
 * rules stay with the caller).
 */
export function formatNumber(value: number, decimals: number): string {
  return new Intl.NumberFormat(getActiveLocale(), {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}
