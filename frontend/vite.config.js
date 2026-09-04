import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const BACKEND_TARGET = process.env.VITE_BACKEND_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Em PRODUCAO o nginx trata /api/ (mesma origem). Em dev, o Vite
      // reencaminha /api/* para o backend removendo o prefixo /api.
      // (paridade com nginx.conf: location /api/ { proxy_pass http://backend:8000/; })
      '/api': {
        target: BACKEND_TARGET,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/webhook': {
        target: BACKEND_TARGET,
        changeOrigin: true,
        secure: false,
      },
      '/health': {
        target: BACKEND_TARGET,
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
