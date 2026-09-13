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
      // ⚠️ 这里不要代理 /problems 和 /submissions ——
      // 它们同时是前端路由（/problems/:id、/problems/:id/submit、/submissions/:id）。
      // 一旦代理出去，开发环境下直接打开或按 F5 这两个路径会拿到后端的裸 JSON，
      // 而不是 SPA 页面（站内跳转因为是客户端路由所以看不出问题，很容易漏掉）。
      // 后端的题目/提交接口全在 /api/ 前缀下，由上面的 '/api' 规则覆盖，不需要单独代理。
      // 线上 nginx 也是这么做的（见 web/nginx.conf 里关于 /judgement、/submissions 的注释）。
      //
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