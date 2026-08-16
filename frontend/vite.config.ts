import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // 前端请求这些路径时自动转发到后端 8000，避免跨域
      // 注意：API key 全部在后端，前端不接触任何密钥
      '/ask': { target: 'http://localhost:8000', changeOrigin: true },
      '/documents': { target: 'http://localhost:8000', changeOrigin: true },
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
