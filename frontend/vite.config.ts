/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
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
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    globals: true,
  },
  build: {
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) {
            return undefined
          }

          if (
            id.includes('/react/') ||
            id.includes('/react-dom/') ||
            id.includes('/react-router-dom/')
          ) {
            return 'react-vendor'
          }

          if (
            id.includes('/@mantine/core/') ||
            id.includes('/@mantine/hooks/') ||
            id.includes('/@mantine/notifications/')
          ) {
            return 'mantine-vendor'
          }

          if (
            id.includes('/@tanstack/react-query/') ||
            id.includes('/axios/') ||
            id.includes('/zustand/')
          ) {
            return 'data-vendor'
          }

          if (
            id.includes('/i18next/') ||
            id.includes('/react-i18next/')
          ) {
            return 'i18n-vendor'
          }

          if (id.includes('/@tabler/icons-react/')) {
            return 'icons-vendor'
          }

          return undefined
        },
      },
    },
  },
})
