import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 规格书 4.1 / AC-2：前端工作台固定运行在 http://127.0.0.1:5178
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5178,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8012',
        changeOrigin: true,
      },
    },
  },
})
