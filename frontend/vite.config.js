import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// In development, /api/* is forwarded to FastAPI on port 8000, so the browser talks to one
// origin, exactly like production on Vercel (frontend and API on the same domain).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
