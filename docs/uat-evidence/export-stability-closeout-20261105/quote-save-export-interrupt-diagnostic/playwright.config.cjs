const { defineConfig } = require('../../../../frontend/node_modules/@playwright/test');
module.exports = defineConfig({ testDir: __dirname, testMatch: 'quote-copy.spec.mjs', timeout: 30000, retries: 0, workers: 1, reporter: [['list']], use: { baseURL: process.env.DIAG_BASE_URL, browserName: 'chromium', channel: 'chrome', acceptDownloads: true } });
