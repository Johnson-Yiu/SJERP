import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import os from 'node:os'
import { runJsonFixture } from '../browser-tests/helpers/json-fixture-process.mjs'

test('CRM JSON snapshots larger than one MiB retain all Unicode field values', () => {
  const text = '合成快照'.repeat(150000)
  const result = runJsonFixture(process.execPath, ['-e',
    "process.stdout.write(JSON.stringify({'crm.SyntheticEvidence':[{id:7,text:'合成快照'.repeat(150000)}]}))"])
  assert.equal(result.status, 0)
  assert.ok(Buffer.byteLength(result.stdout, 'utf8') > 1024 * 1024)
  assert.deepEqual(JSON.parse(result.stdout), { 'crm.SyntheticEvidence': [{ id: 7, text }] })
})

test('fixture launch failure includes the real error code instead of a null status assertion', () => {
  assert.throws(() => runJsonFixture(path.join(os.tmpdir(), 'sunjack-nonexistent-fixture-executable'), []),
    /JSON fixture process failed:.*ENOENT/)
})
