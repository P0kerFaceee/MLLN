import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    open: true,
    port: 8018,
    host: '0.0.0.0',  // 允许移动端访问
    proxy: {
      '/api': 'http://localhost:8999',
      '/uploads': 'http://localhost:8999',
    },
  },
})