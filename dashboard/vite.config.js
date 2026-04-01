import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    // Allow all hosts — required for Coolify reverse proxy
    allowedHosts: [
      'tastebase.web2data.org',
      'localhost'
    ],
  },
});
