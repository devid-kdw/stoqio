import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        // Use IPv4 loopback to avoid macOS AirPlay binding conflicts on localhost:5000.
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
})
