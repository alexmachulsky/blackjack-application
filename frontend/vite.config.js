import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      // Forward all API calls through the Vite dev server to the backend
      // container using its Docker internal hostname.
      // This means the browser always talks to localhost:3000 — no port issues.
      '/auth': { target: 'http://backend:8000', changeOrigin: true },
      '/game': { target: 'http://backend:8000', changeOrigin: true },
      '/stats': { target: 'http://backend:8000', changeOrigin: true },
      '/health': { target: 'http://backend:8000', changeOrigin: true },
    },
  },
})
