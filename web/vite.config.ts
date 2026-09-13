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
      },
      // 后端托管的静态资源（上传的图片 / 头像）。
      // 线上由 nginx 的 `location /static/` 反代，开发环境必须一并代理，
      // 否则会被 Vite 的 SPA 兜底成 index.html，图片全部加载不出来。
      '/static': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      }
    }
  }
})