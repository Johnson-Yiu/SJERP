// Mechanical redaction only: preserve commands, assertions, failures and results.
import { readdir, readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = path.dirname(fileURLToPath(import.meta.url))
for (const name of await readdir(root)) {
  if (!name.endsWith('.txt')) continue
  const file = path.join(root, name)
  const original = await readFile(file, 'utf8')
  const redacted = original
    .replace(/(['"]token['"]\s*:\s*['"])[^'"]+(['"])/g, '$1[REDACTED-RUNTIME-NONCE]$2')
    .replace(/(\/api\/__test__\/isolation\/)[^/\s]+/g, '$1[REDACTED-RUNTIME-NONCE]')
  if (redacted !== original) await writeFile(file, redacted)
}
