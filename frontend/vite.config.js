import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const FILE_EXTS = /\.(md|csv)(\?|$)/
function bypassNav(req) {
  if (req.headers.accept?.includes('text/html') && !FILE_EXTS.test(req.url)) return req.url
}

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/generate': 'http://localhost:8000',
      '/stream': 'http://localhost:8000',
      '/result': { target: 'http://localhost:8000', bypass: bypassNav },
      '/history': { target: 'http://localhost:8000', bypass: bypassNav },
      '/analytics': { target: 'http://localhost:8000', bypass: bypassNav },
      '/jobs': 'http://localhost:8000',
    },
  },
})
