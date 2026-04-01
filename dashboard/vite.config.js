import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    host: true, // or '0.0.0.0'
    allowedHosts: [
      'tastebase.web2data.org'
    ],
  },
});
