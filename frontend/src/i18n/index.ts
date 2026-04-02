import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import hr from './locales/hr.json'
import en from './locales/en.json'
import de from './locales/de.json'
import hu from './locales/hu.json'

i18n.use(initReactI18next).init({
  resources: {
    hr: { translation: hr },
    en: { translation: en },
    de: { translation: de },
    hu: { translation: hu },
  },
  lng: 'hr',
  // Phase 1 lock:
  // - hr is the primary fallback for the app runtime
  // - de/hu intentionally fall back to hr while their locale files remain empty
  // - en can also fall back to hr for any shared runtime key not translated yet
  fallbackLng: (code) => {
    const base = code?.split('-')[0]?.toLowerCase()

    if (base === 'en') {
      return ['hr']
    }

    return ['hr']
  },
  interpolation: {
    escapeValue: false,
  },
})

export default i18n
