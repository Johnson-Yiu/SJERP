import fs from 'node:fs'
import path from 'node:path'

const evidenceDir = process.env.R1_REPAIR_04_EVIDENCE_DIR
  ? path.resolve(process.env.R1_REPAIR_04_EVIDENCE_DIR)
  : null

function safeName(value) {
  return value.replace(/[^a-z0-9_-]+/gi, '-').replace(/^-+|-+$/g, '').toLowerCase()
}

export function evidencePath(name) {
  if (!evidenceDir) return null
  fs.mkdirSync(evidenceDir, { recursive: true })
  return path.join(evidenceDir, name)
}

export async function installRepair04Diagnostics(page, label) {
  const events = {
    label,
    blockedOptionalFonts: true,
    fontInterceptions: [],
    console: [],
    pageErrors: [],
    failedRequests: [],
    apiResponses: [],
    nonSuccessfulResponses: [],
  }

  page.on('console', message => {
    if (message.type() === 'error' || message.type() === 'warning') {
      events.console.push({ type: message.type(), text: message.text() })
    }
  })
  page.on('pageerror', error => events.pageErrors.push(String(error)))
  page.on('requestfailed', request => {
    events.failedRequests.push({ url: request.url(), method: request.method(), failure: request.failure() })
  })
  page.on('response', response => {
    const entry = { url: response.url(), method: response.request().method(), status: response.status() }
    if (response.url().includes('/api/')) events.apiResponses.push(entry)
    if (response.status() >= 400) events.nonSuccessfulResponses.push(entry)
  })

  // These fonts are optional; the app has local fallback fonts. Blocking them
  // makes page navigation and screenshots deterministic when the test machine
  // cannot reach Google Fonts, without changing product code or assertions.
  await page.route('https://fonts.googleapis.com/**', async route => {
    events.fontInterceptions.push({ url: route.request().url(), host: 'fonts.googleapis.com' })
    await route.abort()
  })
  await page.route('https://fonts.gstatic.com/**', async route => {
    events.fontInterceptions.push({ url: route.request().url(), host: 'fonts.gstatic.com' })
    await route.abort()
  })

  return {
    fontRoutesRegistered: true,
    get fontInterceptionCount() {
      return events.fontInterceptions.length
    },
    async save() {
      const target = evidencePath(`${safeName(label)}-diagnostics.json`)
      if (target) fs.writeFileSync(target, `${JSON.stringify(events, null, 2)}\n`, 'utf8')
    },
  }
}
