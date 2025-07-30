import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
	plugins: [react(), tailwindcss()],
	test: {
		environment: 'happy-dom',
		setupFiles: ['./src/test/setup.ts'],
		include: ['src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
		exclude: ['e2e/**/*', 'node_modules/**/*', 'dist/**/*'],
		globals: true,
		css: true,
		env: {
			      VITE_API_BASE_URL: process.env.VITE_API_BASE_URL || 'http://localhost:8003',
      VITE_WS_BASE_URL: process.env.VITE_WS_BASE_URL || 'ws://localhost:8003'
		}
	},
})