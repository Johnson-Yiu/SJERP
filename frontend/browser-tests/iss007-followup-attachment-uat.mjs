import { createHash } from 'node:crypto'
import { mkdir, readFile } from 'node:fs/promises'
import { createRequire } from 'node:module'
import path from 'node:path'
const require = createRequire(import.meta.url)
const { chromium } = require('@playwright/test')

const config = globalThis.ISS007_UAT_CONFIG || {}
const frontendBase = config.frontendBase || 'http://127.0.0.1:5279'
const apiBase = config.apiBase || 'http://127.0.0.1:8177'
const evidenceDir = config.evidenceDir
const downloadDir = config.downloadDir
const operator = config.operator || 'iss007-uat-operator'
const noPermissionUser = config.noPermissionUser || 'iss007-uat-no-permission'
const password = config.password
const subject = 'ISS007附件流程核验 2026-10-31'
const previewName = 'ISS007-preview.txt'
const downloadName = 'ISS007-download.bin'
const deleteName = 'ISS007-delete-target.txt'
if (!evidenceDir || !downloadDir || !password) {
  throw new Error('ISS007_UAT_CONFIG 必须提供 evidenceDir、downloadDir 和临时测试密码。')
}

await mkdir(evidenceDir, { recursive: true })
await mkdir(downloadDir, { recursive: true })

const browser = await chromium.launch({
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: false,
})
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true })
const mediaResponses = []
context.on('response', response => {
  if (response.url().includes('/api/media/')) {
    mediaResponses.push({ status: response.status(), url: new URL(response.url()).pathname })
  }
})

async function login(page, username) {
  await page.goto(`${apiBase}/admin/login/`, { waitUntil: 'domcontentloaded' })
  if (new URL(page.url()).pathname === '/admin/login/') {
    await page.locator('#id_username').fill(username)
    await page.locator('#id_password').fill(password)
    await page.locator('input[type="submit"]').click()
    await page.waitForURL(url => url.pathname.startsWith('/admin/'))
  }
  if (await page.locator('.errornote').count()) {
    throw new Error(`隔离测试账号 ${username} 登录失败。`)
  }
}

async function openFollowUpEditor(page) {
  await page.goto(`${frontendBase}/follow-ups`, { waitUntil: 'domcontentloaded' })
  const row = page.locator('tr').filter({ hasText: subject })
  await row.waitFor({ state: 'visible' })
  await row.getByRole('button', { name: '编辑跟进记录' }).click()
  const editor = page.locator('.crm-editor')
  await editor.waitFor({ state: 'visible' })
  return editor
}

function mediaPathFromHref(href) {
  const parsed = new URL(href, frontendBase)
  if (!parsed.pathname.startsWith('/api/media/')) throw new Error(`非受保护媒体 URL：${parsed.pathname}`)
  return parsed.pathname
}

async function captureEditor(page, editor, filename) {
  await editor.locator('.follow-up-attachment-editor').scrollIntoViewIfNeeded()
  await page.screenshot({ path: path.join(evidenceDir, filename), fullPage: false })
}

async function runBeforeDelete() {
  const page = await context.newPage()
  await login(page, operator)
  const operatorState = await page.evaluate(async () => {
    const response = await fetch('/api/session/current-operator/')
    return response.json()
  })
  if (!operatorState.authenticated || operatorState.name !== 'ISS007合成测试操作员' || operatorState.development_superadmin) {
    throw new Error(`当前浏览器没有使用预期的隔离认证操作人：${JSON.stringify(operatorState)}`)
  }

  const editor = await openFollowUpEditor(page)
  const input = editor.locator('.follow-up-attachment-picker input[type="file"]')
  await input.setInputFiles([
    { name: previewName, mimeType: 'text/plain', buffer: Buffer.from('ISS007 synthetic preview body\n第二行：仅为合成附件。\n', 'utf8') },
    { name: downloadName, mimeType: 'application/octet-stream', buffer: Buffer.from([0, 1, 2, 3, 250, 251, 252, 253]) },
    { name: deleteName, mimeType: 'text/plain', buffer: Buffer.from('ISS007 disposable delete target\n', 'utf8') },
  ])
  for (const name of [previewName, downloadName, deleteName]) {
    await editor.getByText(name, { exact: true }).waitFor({ state: 'visible' })
  }
  await page.screenshot({ path: path.join(evidenceDir, 'desktop-pending-attachments-1440x900.png'), fullPage: false })

  const uploadResponsePromise = page.waitForResponse(response =>
    response.request().method() === 'POST' && response.url().includes('/api/follow-ups/1/attachments/'),
  )
  await editor.getByRole('button', { name: '保存跟进' }).click()
  const uploadResponse = await uploadResponsePromise
  if (uploadResponse.status() !== 201) throw new Error(`附件上传 HTTP ${uploadResponse.status()}，预期 201。`)
  await editor.waitFor({ state: 'hidden' })

  await page.reload({ waitUntil: 'domcontentloaded' })
  const reopenedEditor = await openFollowUpEditor(page)
  for (const name of ['ISS007-legacy-history.txt', previewName, downloadName, deleteName]) {
    await reopenedEditor.getByText(name, { exact: true }).waitFor({ state: 'visible' })
  }
  await captureEditor(page, reopenedEditor, 'desktop-saved-reopened-1440x900.png')

  const layout = await page.evaluate(() => {
    const modal = document.querySelector('.crm-editor')
    const attachmentList = document.querySelector('.follow-up-attachment-editor-list')
    const modalRect = modal?.getBoundingClientRect()
    return {
      viewport: { width: innerWidth, height: innerHeight },
      documentScrollWidth: document.documentElement.scrollWidth,
      modalLeft: modalRect?.left,
      modalRight: modalRect?.right,
      attachmentColumns: attachmentList ? getComputedStyle(attachmentList).gridTemplateColumns : null,
    }
  })

  const previewItem = reopenedEditor.locator('.follow-up-attachment-editor-item.saved').filter({ hasText: previewName })
  const previewHref = await previewItem.getByRole('link', { name: '查看' }).getAttribute('href')
  const previewPath = mediaPathFromHref(previewHref)
  const previewPagePromise = context.waitForEvent('page')
  await previewItem.getByRole('link', { name: '查看' }).click()
  const previewPage = await previewPagePromise
  await previewPage.waitForLoadState('domcontentloaded')
  const previewText = await previewPage.locator('body').innerText()
  if (!previewText.includes('ISS007 synthetic preview body')) throw new Error('Chrome 未能预览合成文本附件。')
  await previewPage.screenshot({ path: path.join(evidenceDir, 'desktop-preview-text-1440x900.png'), fullPage: false })

  const downloadItem = reopenedEditor.locator('.follow-up-attachment-editor-item.saved').filter({ hasText: downloadName })
  const downloadHref = await downloadItem.getByRole('link', { name: '查看' }).getAttribute('href')
  const downloadPath = mediaPathFromHref(downloadHref)
  const downloadPage = await context.newPage()
  const downloadPromise = downloadPage.waitForEvent('download')
  try {
    await downloadPage.goto(`${frontendBase}${downloadPath}`, { waitUntil: 'domcontentloaded' })
  } catch (error) {
    if (!String(error).toLowerCase().includes('download')) throw error
  }
  const download = await downloadPromise
  if (download.suggestedFilename() !== downloadName) throw new Error(`下载文件名异常：${download.suggestedFilename()}`)
  const downloadedPath = path.join(downloadDir, downloadName)
  await download.saveAs(downloadedPath)
  const downloadedBytes = await readFile(downloadedPath)
  const expectedBytes = Buffer.from([0, 1, 2, 3, 250, 251, 252, 253])
  const downloadSha256 = createHash('sha256').update(downloadedBytes).digest('hex')
  if (!downloadedBytes.equals(expectedBytes)) throw new Error('Chrome 下载文件内容与上传合成字节不一致。')

  const authorizedMedia = await page.evaluate(async url => {
    const response = await fetch(url, { credentials: 'include' })
    const bytes = new Uint8Array(await response.arrayBuffer())
    return {
      status: response.status,
      cacheControl: response.headers.get('cache-control'),
      contentType: response.headers.get('content-type'),
      contentDisposition: response.headers.get('content-disposition'),
      byteLength: bytes.length,
      text: new TextDecoder().decode(bytes),
    }
  }, previewPath)
  if (authorizedMedia.status !== 200 || authorizedMedia.cacheControl !== 'private, no-store') {
    throw new Error(`授权直接 URL 响应不符合预期：${JSON.stringify(authorizedMedia)}`)
  }

  const anonymousContext = await browser.newContext()
  const anonymousPage = await anonymousContext.newPage()
  const anonymousResponse = await anonymousPage.goto(`${apiBase}${previewPath}`, { waitUntil: 'domcontentloaded' })
  const anonymousBody = await anonymousPage.locator('body').innerText()
  const noPermissionContext = await browser.newContext()
  const noPermissionPage = await noPermissionContext.newPage()
  await login(noPermissionPage, noPermissionUser)
  const noPermissionResponse = await noPermissionPage.goto(`${apiBase}${previewPath}`, { waitUntil: 'domcontentloaded' })
  const noPermissionBody = await noPermissionPage.locator('body').innerText()
  const staticResponse = await noPermissionPage.goto(`${apiBase}/media/${previewPath.slice('/api/media/'.length)}`, { waitUntil: 'domcontentloaded' })
  const legacyResponse = await noPermissionPage.goto(`${apiBase}/api/media/follow-up-attachments/2024/01/ISS007-legacy-history.txt`, { waitUntil: 'domcontentloaded' })

  await page.setViewportSize({ width: 390, height: 844 })
  await reopenedEditor.locator('.follow-up-attachment-editor').scrollIntoViewIfNeeded()
  await page.screenshot({ path: path.join(evidenceDir, 'mobile-saved-refresh-390x844.png'), fullPage: false })
  const mobileLayout = await page.evaluate(() => {
    const modalRect = document.querySelector('.crm-editor')?.getBoundingClientRect()
    return {
      viewport: { width: innerWidth, height: innerHeight },
      documentScrollWidth: document.documentElement.scrollWidth,
      modalLeft: modalRect?.left,
      modalRight: modalRect?.right,
      attachmentColumns: getComputedStyle(document.querySelector('.follow-up-attachment-editor-list')).gridTemplateColumns,
    }
  })
  if (mobileLayout.viewport.width !== 390 || mobileLayout.viewport.height !== 844 || mobileLayout.documentScrollWidth > 390) {
    throw new Error(`390px 布局超出视口：${JSON.stringify(mobileLayout)}`)
  }

  const result = {
    phase: 'before-delete',
    browser: await browser.version(),
    authenticatedOperator: operatorState.name,
    uploadStatus: uploadResponse.status(),
    reopenedNames: ['ISS007-legacy-history.txt', previewName, downloadName, deleteName],
    authorizedPreview: { path: previewPath, ...authorizedMedia, bodyTextSha256: createHash('sha256').update(authorizedMedia.text).digest('hex') },
    previewTabText: previewText,
    browserDownload: { filename: download.suggestedFilename(), bytes: downloadedBytes.length, sha256: downloadSha256 },
    anonymousDirect: { status: anonymousResponse.status(), body: anonymousBody },
    authenticatedNoPermissionDirect: { status: noPermissionResponse.status(), body: noPermissionBody },
    legacyStaticMediaStatus: staticResponse.status(),
    legacyProtectedMediaNoPermissionStatus: legacyResponse.status(),
    desktopLayout: layout,
    mobileLayout,
    mediaResponses,
    note: 'This phase intentionally stops before deleting the isolated disposable attachment; desktop/mobile screenshots and transfer/access checks are complete.',
  }
  console.log(JSON.stringify(result, null, 2))
  await anonymousContext.close()
  await noPermissionContext.close()
  globalThis.iss007MainPage = page
  globalThis.iss007Editor = reopenedEditor
  return result
}

async function runDeletePhase() {
  const page = await context.newPage()
  await login(page, operator)
  const editor = await openFollowUpEditor(page)
  const disposable = editor.locator('.follow-up-attachment-editor-item.saved').filter({ hasText: deleteName })
  const deletedPath = mediaPathFromHref(await disposable.getByRole('link', { name: '查看' }).getAttribute('href'))
  await disposable.getByRole('button', { name: `删除已保存附件 ${deleteName}` }).click()
  const dialog = page.getByRole('dialog', { name: '删除附件' })
  await dialog.waitFor({ state: 'visible' })
  await dialog.getByRole('button', { name: '取消' }).click()
  await dialog.waitFor({ state: 'hidden' })
  await disposable.getByText(deleteName, { exact: true }).waitFor({ state: 'visible' })
  await page.screenshot({ path: path.join(evidenceDir, 'desktop-delete-cancelled-1440x900.png'), fullPage: false })

  await disposable.getByRole('button', { name: `删除已保存附件 ${deleteName}` }).click()
  const confirmation = page.getByRole('dialog', { name: '删除附件' })
  await confirmation.waitFor({ state: 'visible' })
  const deleteResponsePromise = page.waitForResponse(response =>
    response.request().method() === 'DELETE' && response.url().includes('/api/follow-ups/1/attachments/'),
  )
  await confirmation.getByRole('button', { name: '确认删除' }).click()
  const deleteResponse = await deleteResponsePromise
  if (deleteResponse.status() !== 204) throw new Error(`合成附件删除 HTTP ${deleteResponse.status()}，预期 204。`)
  await disposable.waitFor({ state: 'detached' })
  await page.screenshot({ path: path.join(evidenceDir, 'desktop-delete-immediate-state-1440x900.png'), fullPage: false })

  await page.reload({ waitUntil: 'domcontentloaded' })
  const reopenedEditor = await openFollowUpEditor(page)
  await reopenedEditor.getByText(deleteName, { exact: true }).waitFor({ state: 'hidden' })
  for (const name of ['ISS007-legacy-history.txt', previewName, downloadName]) {
    await reopenedEditor.getByText(name, { exact: true }).waitFor({ state: 'visible' })
  }
  await page.setViewportSize({ width: 390, height: 844 })
  await captureEditor(page, reopenedEditor, 'mobile-delete-refresh-390x844.png')
  const deletedResponse = await page.goto(`${apiBase}${deletedPath}`, { waitUntil: 'domcontentloaded' })
  const result = {
    phase: 'delete',
    browser: await browser.version(),
    deleteStatus: deleteResponse.status(),
    deletedDirectUrlStatus: deletedResponse.status(),
    refreshedNames: ['ISS007-legacy-history.txt', previewName, downloadName],
    screenshot: 'mobile-delete-refresh-390x844.png',
    cancellationKeptAttachment: true,
  }
  console.log(JSON.stringify(result, null, 2))
  await browser.close()
  return result
}

export { runBeforeDelete, runDeletePhase, browser, context }
