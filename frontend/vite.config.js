import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5191,
    strictPort: true,
    proxy: { '/api': `http://127.0.0.1:${process.env.VITE_API_PROXY_PORT || '8100'}` },
  },
})
