// Local Windows verification against an explicitly started isolated Vite server.
// Avoid owning a nested npm process during Playwright teardown.
import config from './playwright.config.js'
export default { ...config, webServer: undefined, use: { ...config.use, baseURL: 'http://127.0.0.1:5196' } }
