import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue()
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/api/admin': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      },
      '/benben': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      },
      '/tokens': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      },
      '/users': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      },
      '/submissions': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      },
      '/problems': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      }
    }
  }
})