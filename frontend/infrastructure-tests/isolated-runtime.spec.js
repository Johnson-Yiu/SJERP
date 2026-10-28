import { expect, test } from '@playwright/test'
import path from 'node:path'
import os from 'node:os'

const runId = process.env.ISOLATED_TEST_RUN_ID
const token = process.env.ISOLATED_TEST_TOKEN
const tempRoot = process.env.ISOLATED_TEST_ROOT

function isWithin(parent, child) {
  const relative = path.relative(parent, child)
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))
}

test('Vite and proxied Django API belong to this isolated run', async ({ request, baseURL }) => {
  expect(runId).toBeTruthy()
  expect(token).toBeTruthy()
  expect(tempRoot).toBeTruthy()
  expect(isWithin(path.resolve(os.tmpdir()), path.resolve(tempRoot))).toBe(true)

  const viteResponse = await request.get('/__test__/isolation/')
  expect(viteResponse.status()).toBe(200)
  expect(await viteResponse.json()).toEqual({ runId, token })

  const apiResponse = await request.get(`/api/__test__/isolation/${encodeURIComponent(token)}/`)
  expect(apiResponse.status()).toBe(200)
  const apiIdentity = await apiResponse.json()
  expect(apiIdentity.runId).toBe(runId)
  expect(apiIdentity.token).toBe(token)
  expect(path.resolve(apiIdentity.database)).toBe(path.resolve(tempRoot, 'db.sqlite3'))
  expect(path.resolve(apiIdentity.mediaRoot)).toBe(path.resolve(tempRoot, 'media'))
  expect(isWithin(path.resolve(os.tmpdir()), path.resolve(apiIdentity.database))).toBe(true)
  expect(isWithin(path.resolve(os.tmpdir()), path.resolve(apiIdentity.mediaRoot))).toBe(true)
  expect(baseURL).toContain('127.0.0.1:')
})
