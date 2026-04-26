import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/generate': 'http://localhost:8000',
      '/stream': 'http://localhost:8000',
      '/result': 'http://localhost:8000',
      '/history': 'http://localhost:8000',
      '/analytics': 'http://localhost:8000',
      '/jobs': 'http://localhost:8000',
    },
  },
})
