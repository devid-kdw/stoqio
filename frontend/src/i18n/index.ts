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
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false,
  },
})

export default i18n
