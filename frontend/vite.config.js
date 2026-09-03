import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const BACKEND_TARGET = process.env.VITE_BACKEND_TARGET || 'http://localhost:8000'

const backendPaths = [
  '/auth', '/companies', '/customers', '/conversations', '/messages',
  '/config', '/dashboard', '/webhook', '/workflows', '/knowledge',
  '/templates', '/health',
]

function rewritePath(path) {
  if (path.endsWith('/')) return path
  return path + '/'
}

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(
      backendPaths.map((p) => [
        p,
        {
          target: BACKEND_TARGET,
          changeOrigin: true,
          secure: false,
          rewrite: rewritePath,
        },
      ])
    ),
  },
})
