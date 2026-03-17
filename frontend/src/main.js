// src/main.js — TasteBase app entry point
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import i18n from './i18n'

// Global SCSS (reset + layout utilities)
import './assets/scss/main.scss'

// Create and mount the Vue app
const app = createApp(App)

app.use(router)
app.use(i18n)

app.mount('#app')