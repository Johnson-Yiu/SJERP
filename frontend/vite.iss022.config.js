import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Evidence-only Vite config: keep the browser run pinned to the isolated ISS-022 API.
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 54128,
    strictPort: true,
    proxy: {
      '/api': 'http://127.0.0.1:54127',
      '/media': 'http://127.0.0.1:54127',
    },
  },
})
