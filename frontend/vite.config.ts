import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/auth': 'http://backend:8000',
      '/tasks': 'http://backend:8000',
      '/sessions': 'http://backend:8000',
      '/journal': 'http://backend:8000',
      '/dashboard': 'http://backend:8000',
    }
  }
})