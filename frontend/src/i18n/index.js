// src/i18n/index.js — vue-i18n configuration
import { createI18n } from 'vue-i18n'
import fr from './fr.json'
import en from './en.json'

// Retrieve persisted language preference, defaulting to French
const savedLocale = localStorage.getItem('tastebase-locale') || 'fr'

const i18n = createI18n({
    legacy: false,          // Use Composition API mode
    locale: savedLocale,
    fallbackLocale: 'fr',
    messages: { fr, en },
})

export default i18n