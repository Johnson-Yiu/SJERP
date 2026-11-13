import { defineConfig } from 'vite'
import path from 'node:path'
import vue from '@vitejs/plugin-vue'
import { configDefaults } from 'vitest/config'

export default defineConfig({
  plugins: [vue()],
  // Independent acceptance runs may share installed dependencies, never optimizer state.
  cacheDir: process.env.ISOLATED_TEST_ROOT ? path.join(process.env.ISOLATED_TEST_ROOT, 'vite-cache') : undefined,
  test: {
    include: [...configDefaults.include, 'tests/crm-list.vitest.js'],
    exclude: [...configDefaults.exclude, 'browser-tests/**', 'infrastructure-tests/**'],
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
