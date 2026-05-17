import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy API calls to FastAPI backend so you don't hit CORS in dev
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})