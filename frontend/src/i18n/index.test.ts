import { afterEach, describe, expect, it } from 'vitest'

import i18n from './index'

describe('i18n fallback chain', () => {
  afterEach(async () => {
    await i18n.changeLanguage('hr')
  })

  it('falls back from de to hr for missing shared runtime keys', async () => {
    await i18n.changeLanguage('de')

    expect(i18n.t('sidebar.logout')).toBe('Odjava')
    expect(i18n.t('shell.loading.title')).toBe('Učitavanje postavki sustava')
  })

  it('falls back from hu to hr for missing shared runtime keys', async () => {
    await i18n.changeLanguage('hu')

    expect(i18n.t('sidebar.user')).toBe('Korisnik')
    expect(i18n.t('nav.settings')).toBe('Postavke')
  })
})
