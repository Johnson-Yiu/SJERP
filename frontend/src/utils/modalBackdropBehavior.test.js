import assert from 'node:assert/strict'
import { readdir, readFile } from 'node:fs/promises'
import { join } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const sourceRoot = fileURLToPath(new URL('../', import.meta.url))

async function vueFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  const files = []
  for (const entry of entries) {
    const path = join(directory, entry.name)
    if (entry.isDirectory()) files.push(...await vueFiles(path))
    else if (entry.isFile() && entry.name.endsWith('.vue')) files.push(path)
  }
  return files
}

test('business modal backdrops do not close dialogs on outside clicks', async () => {
  const files = await vueFiles(sourceRoot)
  const offenders = []
  for (const file of files) {
    const source = await readFile(file, 'utf8')
    if (/@(?:click|mousedown|pointerdown)\.self\s*=/.test(source)) offenders.push(file)
  }
  assert.deepEqual(offenders, [])
})
