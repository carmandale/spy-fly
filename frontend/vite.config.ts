import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: parseInt(env.PORT || '3003'),
      proxy: {
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://localhost:8003',
          changeOrigin: true,
        }
      }
    }
  }
})