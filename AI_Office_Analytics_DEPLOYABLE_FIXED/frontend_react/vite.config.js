import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// AI Office Analytics — React dashboard
//
// Local dev: builds into ../frontend (also used if Flask serves the
// built frontend itself, same-origin). The proxy below forwards
// /api, /video, /camera_status, /photo, /unknown_photo to Flask on
// :5000 so `npm run dev` works against the real backend without any
// CORS setup.
//
// Production (e.g. deployed on Vercel with the backend deployed
// separately on Render/Railway/etc): this proxy does NOT apply —
// there's no dev server in production. Instead set VITE_API_BASE_URL
// (see .env.example) and src/lib/api.js builds every request against
// that URL directly. The Flask backend has CORS enabled (see
// FRONTEND_ORIGIN in backend/app.py) to allow this.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../frontend',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:5000',
      '/video': 'http://localhost:5000',
      '/camera_status': 'http://localhost:5000',
      '/photo': 'http://localhost:5000',
      '/unknown_photo': 'http://localhost:5000',
    },
  },
})
