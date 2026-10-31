import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 54175,
    strictPort: true,
    proxy: {
      '/api': 'http://127.0.0.1:54174',
      '/media': 'http://127.0.0.1:54174',
    },
  },
})
