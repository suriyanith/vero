/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In Docker Compose the backend is reached by service name; locally by port.
const backendOrigin = process.env.BACKEND_ORIGIN ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // One origin in the browser: session cookies and CSRF work, no CORS.
    // The string shorthand would set changeOrigin (rewriting Host to the
    // backend), which breaks Django's CSRF origin check against the
    // browser's real Origin header — so keep Host as the browser sent it.
    proxy: {
      '/api': { target: backendOrigin, changeOrigin: false },
      '/admin': { target: backendOrigin, changeOrigin: false },
      '/static': { target: backendOrigin, changeOrigin: false },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.ts',
  },
})
