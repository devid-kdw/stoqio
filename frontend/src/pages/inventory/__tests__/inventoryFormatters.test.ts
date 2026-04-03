import { afterAll, beforeAll, describe, expect, it } from 'vitest'

import i18n from '../../../i18n'
import { fmtDiff, fmtQty } from '../inventoryFormatters'

describe('inventoryFormatters', () => {
  let previousLanguage = 'hr'

  beforeAll(async () => {
    previousLanguage = i18n.language
    await i18n.changeLanguage('en')
  })

  afterAll(async () => {
    await i18n.changeLanguage(previousLanguage || 'hr')
  })

  it('formats decimal quantities through the shared locale-aware number helper', () => {
    expect(fmtQty(1234.5, true)).toBe('1,234.50')
  })

  it('keeps integer quantities whole-number formatted', () => {
    expect(fmtQty(5, false)).toBe('5')
  })

  it('prefixes only positive differences with a plus sign', () => {
    expect(fmtDiff(2, true)).toBe('+2.00')
    expect(fmtDiff(-2, true)).toBe('-2.00')
    expect(fmtDiff(0, false)).toBe('0')
  })
})
