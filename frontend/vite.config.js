import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        client: resolve(__dirname, 'index.html'),
        server: resolve(__dirname, 'server.html'),
      },
    },
  },
})
