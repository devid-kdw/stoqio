import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  getActiveLocale,
  formatDate,
  formatDateTime,
  formatNumber,
} from './locale'
import i18n from '../i18n'

vi.mock('../i18n', () => ({
  default: {
    language: 'hr',
  },
}))

describe('locale formatting helpers', () => {
  beforeEach(() => {
    i18n.language = 'hr'
  })

  it('maps known i18n tags to BCP-47 locales correctly', () => {
    i18n.language = 'hr'
    expect(getActiveLocale()).toBe('hr-HR')

    i18n.language = 'en'
    expect(getActiveLocale()).toBe('en-GB')

    i18n.language = 'de-DE'
    expect(getActiveLocale()).toBe('de-DE')

    i18n.language = 'hu'
    expect(getActiveLocale()).toBe('hu-HU')
  })

  it('falls back to hr-HR for unknown languages', () => {
    i18n.language = 'fr'
    expect(getActiveLocale()).toBe('hr-HR')

    // @ts-expect-error fallback scenario
    i18n.language = null
    expect(getActiveLocale()).toBe('hr-HR')
  })

  describe('formatDate', () => {
    it('returns a fallback for null/empty', () => {
      expect(formatDate(null)).toBe('—')
      expect(formatDate('')).toBe('—')
    })

    it('formats a valid date according to the active locale', () => {
      const date = '2026-04-02T12:00:00Z'
      
      i18n.language = 'hr'
      expect(formatDate(date)).toMatch(/0?2\.\s?0?4\.\s?2026\./)

      i18n.language = 'en'
      // en-GB format is DD/MM/YYYY
      expect(formatDate(date)).toMatch(/0?2\/0?4\/2026/)
    })
  })

  describe('formatDateTime', () => {
    it('returns a fallback for null/empty', () => {
      expect(formatDateTime(null)).toBe('—')
    })

    it('formats a valid datetime according to the active locale', () => {
      const date = '2026-04-02T14:30:00Z'
      // 14:30 GMT is 16:30 in CEST
      // depending on timezone where test is run, it could be different, so let's check format structure
      
      i18n.language = 'hr'
      const formattedHr = formatDateTime(date)
      expect(formattedHr).toMatch(/0?2\.\s?0?4\.\s?2026\.?,?\s?\d{2}:\d{2}/)

      i18n.language = 'en'
      const formattedEn = formatDateTime(date)
      expect(formattedEn).toMatch(/0?2\/0?4\/2026,?\s?\d{2}:\d{2}/)
    })
  })

  describe('formatNumber', () => {
    it('formats numbers with the specified minimum and maximum fraction digits based on locale', () => {
      i18n.language = 'hr'
      const num1 = formatNumber(1234.56, 2)
      // hr uses comma for decimal separator and dot for thousand separator
      expect(num1).toBe('1.234,56')

      i18n.language = 'en'
      const num2 = formatNumber(1234.56, 2)
      // en-GB uses dot for decimal and comma for thousand separator
      expect(num2).toBe('1,234.56')
    })

    it('respects zero decimal configurations', () => {
      i18n.language = 'hr'
      expect(formatNumber(1234, 0)).toBe('1.234')
    })
  })
})
