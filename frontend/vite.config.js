import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// Absolute path to _variables.scss — ESM-compatible (no __dirname)
const variablesPath = fileURLToPath(
  new URL('./src/assets/scss/_variables.scss', import.meta.url)
)

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        // Inject @use of _variables.scss at the top of every <style lang="scss"> block.
        // Uses import.meta.url (ESM) instead of __dirname (CJS) for the absolute path.
        // The \n ensures it appears on its own line before any component styles.
        additionalData: `@use "${variablesPath}" as *;\n`,
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Proxy API calls to FastAPI during development
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
