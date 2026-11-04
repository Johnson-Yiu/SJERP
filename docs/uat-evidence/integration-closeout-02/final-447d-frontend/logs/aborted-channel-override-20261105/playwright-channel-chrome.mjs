// Loaded only by Node children of this final-evidence coordinator.
// The unchanged isolated runner intentionally clears PLAYWRIGHT_CHANNEL for
// most profiles; restore the requested real Chrome channel only in Playwright's
// CLI process, without changing the runner or its isolation controls.
const entry = String(process.argv[1] || '').replaceAll('\\', '/').toLowerCase()
if (entry.endsWith('/node_modules/@playwright/test/cli.js')) {
  process.env.PLAYWRIGHT_CHANNEL = 'chrome'
  process.stderr.write('[final-447d] PLAYWRIGHT_CHANNEL=chrome applied to Playwright CLI\n')
}
