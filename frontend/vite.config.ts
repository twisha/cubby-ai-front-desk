import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Dev: this proxy forwards /api/* to FastAPI (uvicorn on 8000) so the SPA and
// backend share an origin during development. Prod: `vite build` -> dist/,
// served by FastAPI's own StaticFiles mount at "/" (single deployable).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
