import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

function isolationIdentityPlugin() {
  return {
    name: 'sunjack-isolated-test-identity',
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        const pathname = new URL(request.url || '/', 'http://127.0.0.1').pathname
        if (pathname !== '/__test__/isolation/') return next()
        response.statusCode = 200
        response.setHeader('content-type', 'application/json; charset=utf-8')
        response.end(JSON.stringify({
          runId: process.env.ISOLATED_TEST_RUN_ID,
          token: process.env.ISOLATED_TEST_TOKEN,
        }))
      })
    },
  }
}

function requiredPort(name) {
  const value = Number(process.env[name])
  if (!Number.isInteger(value) || value < 1 || value > 65535) {
    throw new Error(`${name} must be an explicitly assigned TCP port.`)
  }
  return value
}

export default defineConfig({
  plugins: [vue(), isolationIdentityPlugin()],
  server: {
    host: '127.0.0.1',
    port: requiredPort('ISOLATED_VITE_PORT'),
    strictPort: true,
    proxy: {
      '/api': `http://127.0.0.1:${requiredPort('ISOLATED_API_PORT')}`,
      '/media': `http://127.0.0.1:${requiredPort('ISOLATED_API_PORT')}`,
    },
  },
})
