import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { configDefaults } from 'vitest/config'

export default defineConfig({
  plugins: [vue()],
  test: {
    exclude: [...configDefaults.exclude, 'browser-tests/**'],
    setupFiles: ['./tests/setup.js'],
  },
  server: {
    port: 5191,
    strictPort: true,
    proxy: {
      '/api': `http://127.0.0.1:${process.env.VITE_API_PROXY_PORT || '8100'}`,
      '/media': `http://127.0.0.1:${process.env.VITE_API_PROXY_PORT || '8100'}`,
    },
  },
})
