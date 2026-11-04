import { spawnSync } from 'node:child_process'

// Integrated snapshots include every CRM row, including saved template assets.
// Keep a bounded buffer without dropping rows from no-side-effect assertions.
export function runJsonFixture(executable, args, options = {}) {
  const result = spawnSync(executable, args, {
    ...options, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024,
  })
  if (result.error || result.signal) {
    const diagnostic = {
      code: result.error?.code || null, signal: result.signal,
      status: result.status, stdoutBytes: Buffer.byteLength(result.stdout || '', 'utf8'),
      stderrBytes: Buffer.byteLength(result.stderr || '', 'utf8'),
    }
    throw new Error(`JSON fixture process failed: ${JSON.stringify(diagnostic)}`, { cause: result.error })
  }
  return result
}
